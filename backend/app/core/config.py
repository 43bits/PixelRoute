"""
Configuration settings loaded from environment variables
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_SECRET_KEY: str = "change-this-to-a-random-secret-key"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database
    DATABASE_URL: str
    
    # Bright Data
    BRIGHT_DATA_API_TOKEN: str
    BRIGHT_DATA_CUSTOMER_ID: str
    BRIGHT_DATA_API_URL: str = "https://api.brightdata.com"
    
    # PixelRAG
    PIXELRAG_MODEL: str = "Qwen/Qwen3-VL-Embedding-2B"
    PIXELRAG_DEVICE: str = "auto"
    PIXELRAG_INDEX_PATH: str = "./data/index"
    
    # Vector Storage
    VECTOR_BACKEND: str = "faiss"  # faiss or qdrant
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "visualqa_scraper"
    
    # Storage
    STORAGE_PATH: str = "./data/storage"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Token expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


# Create global settings instance
settings = Settings()
