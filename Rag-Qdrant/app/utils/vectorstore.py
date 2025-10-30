# utils/vectorstore.py

import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_community.vectorstores import Qdrant
from ..utils.embeddings import get_embeddings_model  # should return GoogleGenerativeEmbeddings

def get_qdrant_client():
    """Return connected Qdrant client with extended timeout."""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=180)


def get_vectorstore(collection_name: str = "rag_collection", docs=None):
    """
    Initialize or connect to Qdrant vector store and insert documents if provided.
    """
    client = get_qdrant_client()
    embeddings = get_embeddings_model()

    # Determine vector size dynamically from embedding model
    test_vector = embeddings.embed_documents(["test"])[0]
    vector_size = len(test_vector)

    # Ensure collection exists
    collections = client.get_collections()
    if not any(c.name == collection_name for c in collections.collections):
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
        )

    vectorstore = Qdrant(client=client, collection_name=collection_name, embeddings=embeddings)

    # Insert documents in batches if docs provided
    if docs:
        batch_size = 20
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            vectors = embeddings.embed_documents([d.page_content for d in batch])
            points = [
                {
                    "id": str(uuid.uuid4()),
                    "vector": vec,
                    "payload": {**d.metadata, "page_content": d.page_content}
                }
                for d, vec in zip(batch, vectors)
            ]
            client.upsert(collection_name=collection_name, points=points)

    return vectorstore


# --------------------- Delete document from collection ---------------------
def delete_document_from_vectorstore(collection_name: str, doc_id: str):
    """
    Delete a single document from the Qdrant collection using its ID.
    """
    client = get_qdrant_client()
    try:
        client.delete(
            collection_name=collection_name,
            points=[doc_id]
        )
        print(f"Document {doc_id} deleted successfully from collection '{collection_name}'")
    except Exception as e:
        print(f"Failed to delete document {doc_id}: {e}")
