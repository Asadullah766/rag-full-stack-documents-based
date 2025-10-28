# utils/embeddings.py

from langchain_community.embeddings import HuggingFaceEmbeddings

def get_embeddings_model():
    """Return Hugging Face embedding model for vectorization."""
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return embeddings
