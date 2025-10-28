from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    QDRANT_URL: str = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY")
    VECTOR_COLLECTION_NAME: str = os.getenv("COLLECTION_NAME")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL")

settings = Settings()
