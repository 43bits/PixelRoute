"""
Configuration — loaded from environment variables.
Production-safe defaults (DEBUG off, RELOAD off).
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):

    # ── API ────────────────────────────────────────────────────────────────────
    API_HOST:       str  = "0.0.0.0"
    API_PORT:       int  = 8000
    API_RELOAD:     bool = False          # must be False in production
    API_SECRET_KEY: str  = "change-me"
    DEBUG:          bool = False

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Accepts a JSON array  ["https://x.vercel.app","http://localhost:3000"]
    # OR a comma-separated string  https://x.vercel.app,http://localhost:3000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Bright Data ────────────────────────────────────────────────────────────
    BRIGHT_DATA_API_TOKEN:   str = ""
    BRIGHT_DATA_COLLECTOR_ID: str = ""
    BRIGHT_DATA_API_URL:     str = "https://api.brightdata.com"

    # ── PixelRAG (optional on free tier) ──────────────────────────────────────
    PIXELRAG_MODEL:      str = "Qwen/Qwen3-VL-Embedding-2B"
    PIXELRAG_DEVICE:     str = "auto"
    PIXELRAG_INDEX_PATH: str = "./data/index"

    # ── Vector storage ─────────────────────────────────────────────────────────
    VECTOR_BACKEND:          str = "faiss"
    QDRANT_URL:              str = ""
    QDRANT_API_KEY:          str = ""
    QDRANT_COLLECTION_NAME:  str = "visualqa_scraper"

    # ── Storage ────────────────────────────────────────────────────────────────
    STORAGE_PATH:    str = "./data/storage"
    MAX_UPLOAD_SIZE: int = 10485760   # 10 MB

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Auth ───────────────────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
