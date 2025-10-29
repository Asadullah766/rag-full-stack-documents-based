import os
import time
import uuid
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import Qdrant
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from app.config import settings
from langchain.memory import ConversationBufferMemory


class RAGPipeline:
    def __init__(self):
        # ---- Basic configs ----
        self.embedding_model = settings.EMBEDDING_MODEL
        self.qdrant_url = settings.QDRANT_URL
        self.qdrant_api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.VECTOR_COLLECTION_NAME
        self.gemini_api_key = settings.GEMINI_API_KEY

        # ---- Conversation Memory ----
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

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
            raise ValueError("Unsupported file type!")
        return loader.load()

    # ---------------- Text splitting ----------------
    def split_text(self, documents):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len
        )
        return splitter.split_documents(documents)

    # ---------------- Embeddings ----------------
    def get_embeddings(self):
        return HuggingFaceEmbeddings(model_name=self.embedding_model)

    # ---------------- Store documents in Qdrant ----------------
    def store_in_qdrant(self, docs, embeddings):
        try:
            return Qdrant.from_documents(
                docs,
                embeddings,
                url=self.qdrant_url,
                collection_name=self.collection_name,
                api_key=self.qdrant_api_key,
                prefer_grpc=False,
            )
        except Exception as e:
            print(f"⚠️ Qdrant direct insert failed, retrying manually: {e}")
            time.sleep(2)
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=180)
            vector_size = len(embeddings.embed_documents(["test"])[0])

            try:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
            except Exception:
                pass

            batch_size = 20
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i + batch_size]
                vectors = embeddings.embed_documents([d.page_content for d in batch])
                points = [
                    {
                        "id": str(uuid.uuid4()),
                        "vector": v,
                        "payload": {**d.metadata, "page_content": d.page_content}
                    }
                    for d, v in zip(batch, vectors)
                ]
                client.upsert(collection_name=self.collection_name, points=points)
                print(f"Inserted {min(i + batch_size, len(docs))}/{len(docs)}")

            return Qdrant(client=client, collection_name=self.collection_name, embeddings=embeddings)

    # ---------------- Ingest plain text ----------------
    def ingest_text(self, text):
        if not text.strip():
            raise ValueError("Text content is empty!")

        docs = [Document(page_content=text)]
        chunks = self.split_text(docs)
        embeddings = self.get_embeddings()
        self.store_in_qdrant(chunks, embeddings)
        return len(chunks)

    # ---------------- Ask query ----------------
    def ask(self, query):
        try:
            if not query.strip():
                return {"error": "Query is missing"}

            embeddings = self.get_embeddings()
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=180)
            qdrant_store = Qdrant(client=client, collection_name=self.collection_name, embeddings=embeddings)
            retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})

            related_docs = retriever.get_relevant_documents(query)
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
                model="gemini-2.0-flash-exp",
                google_api_key=self.gemini_api_key,
                temperature=0.3,
            )
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)

            self.memory.save_context({"input": query}, {"output": answer})

            return {"answer": answer}

        except Exception as e:
            return {"error": f"❌ Gemini request failed: {str(e)}"}

    # ---------------- Ask query streaming ----------------
    def ask_stream(self, query):
        """
        Generator to yield response text line by line (or chunk by chunk)
        """
        try:
            if not query.strip():
                yield "Error: Query is missing"
                return

            embeddings = self.get_embeddings()
            client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=180)
            qdrant_store = Qdrant(client=client, collection_name=self.collection_name, embeddings=embeddings)
            retriever = qdrant_store.as_retriever(search_kwargs={"k": 4})

            related_docs = retriever.get_relevant_documents(query)
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
                model="gemini-2.0-flash-exp",
                google_api_key=self.gemini_api_key,
                temperature=0.3,
                max_output_tokens=500
            )

            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)

            for line in answer.split("\n"):
                yield line + "\n"
                time.sleep(0.05)

            self.memory.save_context({"input": query}, {"output": answer})

        except Exception as e:
            yield f"❌ Gemini request failed: {str(e)}\n"
