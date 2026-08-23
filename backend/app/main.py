"""
VisualQA-Scraper Backend
FastAPI application with Bright Data and PixelRAG integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from loguru import logger

from app.core.config import settings
from app.core.database import prisma
from app.api import scrapers, jobs, query, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting VisualQA-Scraper API...")
    
    # Connect to database
    await prisma.connect()
    logger.info("Database connected")
    
    # Initialize PixelRAG
    from app.services.pixelrag import initialize_pixelrag
    await initialize_pixelrag()
    logger.info("PixelRAG initialized")
    
    # Create storage directories
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.PIXELRAG_INDEX_PATH, exist_ok=True)
    logger.info("Storage directories ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await prisma.disconnect()
    logger.info("Database disconnected")


# Create FastAPI app
app = FastAPI(
    title="VisualQA-Scraper API",
    description="Self-healing web scraper with visual RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(scrapers.router, prefix="/api/scrapers", tags=["Scrapers"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "VisualQA-Scraper API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
