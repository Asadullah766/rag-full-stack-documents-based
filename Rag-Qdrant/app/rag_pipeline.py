import os
import time
import uuid
import hashlib

# Document loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader,
)

# Text splitting
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Conversation memory
from langchain.memory import ConversationBufferMemory

# Document schema
from langchain.schema import Document

# Vector store + Embeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_community.embeddings import HuggingFaceEmbeddings

# Config + Utils
from app.config import settings
from app.utils.embeddings import get_embeddings_model
from langchain_google_genai import ChatGoogleGenerativeAI


class RAGPipeline:
    def __init__(self):
        # ---- Basic configs ----
        self.embedding_model = get_embeddings_model()
        self.qdrant_url = settings.QDRANT_URL
        self.qdrant_api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.VECTOR_COLLECTION_NAME
        self.gemini_api_key = settings.GEMINI_API_KEY

        # ---- Conversation Memory ----
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        # ---- Qdrant Client ----
        self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=180)

        # ✅ Auto detect embedding dimension (384 / 768 / etc)
        try:
            self.vector_size = len(self.embedding_model.embed_query("test"))
        except Exception as e:
            print(f"⚠️ Could not detect embedding size automatically: {e}")
            self.vector_size = 768  # fallback default

        # Ensure collection setup
        self._ensure_collection()

    # ---------------- Ensure Qdrant collection exists ----------------
    def _ensure_collection(self):
        try:
            if self.collection_name not in [c.name for c in self.client.get_collections().collections]:
                print(f"🆕 Creating Qdrant collection '{self.collection_name}' (dim={self.vector_size})...")
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
                print(f"✅ Collection '{self.collection_name}' created successfully.")
            else:
                print(f"✅ Collection '{self.collection_name}' already exists.")
        except Exception as e:
            print(f"❌ Failed to ensure collection: {e}")

    # ---------------- File loading ----------------
    def load_file(self, file_path):
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path)
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        elif ext == ".csv":
            loader = CSVLoader(file_path)
        else:
            raise ValueError("❌ Unsupported file type!")
        return loader.load()

    # ---------------- Text splitting ----------------
    def split_text(self, documents):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
        )
        return splitter.split_documents(documents)

    # ---------------- Unique hash for deduplication ----------------
    def _doc_hash(self, doc: Document):
        content = doc.page_content or ""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ---------------- Store documents in Qdrant ----------------
    def store_in_qdrant(self, docs):
        if not docs:
            print("⚠️ No documents to insert into Qdrant.")
            return 0

        inserted_count = 0
        batch_size = 20

        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            points_to_insert = []

            for d in batch:
                try:
                    vector = self.embedding_model.embed_documents([d.page_content])[0]
                    points_to_insert.append({
                        "id": str(uuid.uuid4()),
                        "vector": vector,
                        "payload": {
                            "page_content": d.page_content,
                            **d.metadata,
                            "doc_hash": self._doc_hash(d),
                        },
                    })
                except Exception as e:
                    print(f"⚠️ Skipped a document chunk due to embedding error: {e}")

            if points_to_insert:
                try:
                    self.client.upsert(collection_name=self.collection_name, points=points_to_insert)
                    inserted_count += len(points_to_insert)
                except Exception as e:
                    print(f"❌ Failed to upsert batch: {e}")

        print(f"✅ Inserted {inserted_count} documents into Qdrant.")
        return inserted_count

    # ---------------- Ingest plain text ----------------
    def ingest_text(self, text):
        if not text.strip():
            raise ValueError("⚠️ Text content is empty!")
        docs = [Document(page_content=text)]
        chunks = self.split_text(docs)
        return self.store_in_qdrant(chunks)

    # ---------------- Ask query ----------------
    def ask(self, query):
        if not query.strip():
            return {"error": "Query is missing"}

        qdrant_store = Qdrant(
            client=self.client,
            collection_name=self.collection_name,
            embeddings=self.embedding_model,
        )
        retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})
        related_docs = retriever.get_relevant_documents(query)

        if not related_docs:
            return {"answer": "No relevant context found in Qdrant."}

        context = "\n".join([d.page_content for d in related_docs])
        chat_history = self.memory.load_memory_variables({}).get("chat_history", "")

        prompt = f"""
Previous conversation:
{chat_history}

User asked: {query}

Relevant context:
{context}

Answer clearly, accurately, and conversationally:
"""

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=self.gemini_api_key,
            temperature=0.3,
            max_output_tokens=500,
        )

        try:
            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))
            self.memory.save_context({"input": query}, {"output": answer})
            return {"answer": answer}
        except Exception as e:
            return {"error": f"Gemini API failed: {e}"}

    # ---------------- Ask query (Streaming) ----------------
    def ask_stream(self, query):
        try:
            if not query.strip():
                yield "Error: Query is missing"
                return

            qdrant_store = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embedding_model,
            )

            retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})
            related_docs = retriever.get_relevant_documents(query)

            if not related_docs:
                yield "No relevant documents found.\n"
                return

            context = "\n".join([d.page_content for d in related_docs])
            chat_history = self.memory.load_memory_variables({}).get("chat_history", "")

            prompt = f"""
Previous conversation:
{chat_history}

User asked: {query}

Relevant context:
{context}

Answer clearly and conversationally:
"""

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                api_key=self.gemini_api_key,
                temperature=0.3,
                max_output_tokens=500,
            )

            response = llm.invoke(prompt)
            answer = getattr(response, "content", str(response))

            for line in answer.split("\n"):
                yield line + "\n"
                time.sleep(0.05)

            self.memory.save_context({"input": query}, {"output": answer})

        except Exception as e:
            yield f"❌ Gemini request failed: {str(e)}\n"
