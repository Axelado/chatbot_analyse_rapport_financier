"""
Configuration du chatbot financier
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Provider configuration
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")
    embedding_provider: str = Field(default="local", env="EMBEDDING_PROVIDER")

    # Modèles
    ollama_model: str = Field(default="llama3.2:3b", env="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    
    # ChromaDB
    chroma_persist_directory: str = Field(
        default="./data/chroma_db",
        env="CHROMA_PERSIST_DIRECTORY"
    )
    
    # Traitement PDF
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    
    # Serveur
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Chemins
    reports_directory: str = Field(default="./data/reports", env="REPORTS_DIRECTORY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Retourne les paramètres de l'application (singleton)"""
    return Settings()
