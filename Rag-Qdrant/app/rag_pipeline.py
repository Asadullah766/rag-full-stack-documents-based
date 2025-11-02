import os
import time
import uuid
import hashlib
import traceback

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.utils.embeddings import get_embeddings_model


class RAGPipeline:
    def __init__(self):
        self.embedding_model = get_embeddings_model()
        self.collection_name = settings.VECTOR_COLLECTION_NAME
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL, 
            api_key=settings.QDRANT_API_KEY, 
            timeout=180
        )
        self.gemini_api_key = settings.GEMINI_API_KEY

        # Determine vector size
        try:
            self.vector_size = len(self.embedding_model.embed_query("test"))
        except:
            self.vector_size = 768

        self._ensure_collection()

    # ---------------- Qdrant Collection ----------------
    def _ensure_collection(self):
        existing = [c.name for c in self.qdrant_client.get_collections().collections]
        if self.collection_name not in existing:
            print(f"🆕 Creating collection '{self.collection_name}'")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size, 
                    distance=models.Distance.COSINE
                ),
            )
        else:
            print(f"✅ Collection '{self.collection_name}' exists")

    # ---------------- File loader ----------------
    def load_file(self, path):
        ext = os.path.splitext(path)[-1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(path)
        elif ext == ".txt":
            loader = TextLoader(path)
        elif ext == ".docx":
            loader = Docx2txtLoader(path)
        elif ext == ".csv":
            loader = CSVLoader(path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        return loader.load()

    # ---------------- Text splitting ----------------
    def split_text(self, documents):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=150
        )
        return splitter.split_documents(documents)

    # ---------------- Unique doc hash ----------------
    def _doc_hash(self, doc: Document):
        return hashlib.sha256((doc.page_content or "").encode()).hexdigest()

    # ---------------- Store in Qdrant ----------------
    def store_in_qdrant(self, docs, file_id=None):
        if not docs:
            return 0, file_id

        self._ensure_collection()
        batch_size = 20
        if not file_id:
            file_id = str(uuid.uuid4())
        inserted_count = 0

        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            points = []
            for doc in batch:
                try:
                    vec = self.embedding_model.embed_documents(
                        [doc.page_content]
                    )[0]
                    points.append({
                        "id": str(uuid.uuid4()),
                        "vector": vec,
                        "payload": {
                            **doc.metadata,
                            "page_content": doc.page_content,
                            "doc_hash": self._doc_hash(doc),
                            "file_id": file_id
                        },
                    })
                except Exception as e:
                    print(f"⚠️ Skipped chunk: {e}")

            if points:
                try:
                    self.qdrant_client.upsert(
                        collection_name=self.collection_name, points=points
                    )
                    inserted_count += len(points)
                except Exception as e:
                    print(f"❌ Failed to upsert batch: {e}")

        return inserted_count, file_id

    # ---------------- Ingest plain text ----------------
    def ingest_text(self, text, file_id=None):
        if not text.strip():
            raise ValueError("Text empty")
        docs = [Document(page_content=text)]
        chunks = self.split_text(docs)
        return self.store_in_qdrant(chunks, file_id=file_id)

    # ---------------- Memory ----------------
    def get_memory(self, file_id):
        return ConversationBufferMemory(
            memory_key=f"chat_history_{file_id}", return_messages=True
        )

    # ---------------- Ask ----------------
    def ask(self, query, file_id=None):
        if not query.strip():
            return {"error": "Query missing"}

        memory = (
            self.get_memory(file_id)
            if file_id
            else ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        )
        qdrant_store = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding_model,
        )
        retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})
        related_docs = retriever.get_relevant_documents(query)

        if not related_docs:
            return {"answer": "No relevant context found"}

        context = "\n".join([d.page_content for d in related_docs])
        chat_history = memory.load_memory_variables({}).get(memory.memory_key, "")

        prompt = (
            f"Previous conversation:\n{chat_history}\n"
            f"User asked: {query}\n"
            f"Relevant context:\n{context}\n"
            "Answer clearly:"
        )

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=self.gemini_api_key,
            temperature=0.3,
            max_output_tokens=2000,
        )
        try:
            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))
            memory.save_context({"input": query}, {"output": answer})
            return {"answer": answer}
        except Exception as e:
            return {"error": f"Gemini API failed: {e}"}

    # ---------------- Ask Stream ----------------
    def ask_stream(self, query, file_id=None):
        if not query.strip():
            yield "Query missing"
            return
        memory = (
            self.get_memory(file_id)
            if file_id
            else ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        )
        qdrant_store = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding_model,
        )
        retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})
        related_docs = retriever.get_relevant_documents(query)

        if not related_docs:
            yield "No relevant documents found.\n"
            return

        context = "\n".join([d.page_content for d in related_docs])
        chat_history = memory.load_memory_variables({}).get(memory.memory_key, "")
        prompt = (
            f"Previous conversation:\n{chat_history}\n"
            f"User asked: {query}\n"
            f"Relevant context:\n{context}\n"
            "Answer clearly:"
        )

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=self.gemini_api_key,
            temperature=0.3,
            max_output_tokens=2000,
        )
        try:
            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))
            for line in answer.split("\n"):
                yield line + "\n"
                time.sleep(0.05)
            memory.save_context({"input": query}, {"output": answer})
        except Exception as e:
            yield f"❌ Gemini request failed: {str(e)}\n"
