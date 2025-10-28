# Make app a Python package
from .config import settings
from .rag_pipeline import RAGPipeline

__all__ = ["settings", "RAGPipeline"]
