import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_community.vectorstores import Qdrant
from app.utils.embeddings import get_embeddings_model


def get_qdrant_client():
    """Initialize and return Qdrant client."""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=180)


def get_vectorstore(collection_name="rag_collection", docs=None):
    """
    Create or load a Qdrant vectorstore.
    If docs are provided, they will be embedded and inserted into the collection.
    """
    client = get_qdrant_client()
    embeddings = get_embeddings_model()

    # Get vector size dynamically
    test_vector = embeddings.embed_documents(["test"])[0]
    vector_size = len(test_vector)

    # Ensure collection exists
    collections = client.get_collections()
    if not any(c.name == collection_name for c in collections.collections):
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )

    # Create LangChain-compatible vectorstore
    vectorstore = Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)

    # Optional: ingest documents
    if docs:
        batch_size = 20
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            vectors = embeddings.embed_documents([d.page_content for d in batch])
            points = [
                {
                    "id": str(uuid.uuid4()),
                    "vector": vec,
                    "payload": {**d.metadata, "page_content": d.page_content},
                }
                for d, vec in zip(batch, vectors)
            ]
            client.upsert(collection_name=collection_name, points=points)

    return vectorstore
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
    return text_splitter.split_documents(documents)