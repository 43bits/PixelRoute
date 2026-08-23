"""
Health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime

from app.core.config import settings
from app.core.database import prisma

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status"""
    
    # Check database
    db_healthy = False
    try:
        await prisma.query_raw("SELECT 1")
        db_healthy = True
    except Exception:
        pass
    
    # Check PixelRAG
    pixelrag_healthy = True  # Will check if model is loaded
    
    # Check Bright Data (just check if credentials are set)
    bright_data_configured = bool(
        settings.BRIGHT_DATA_API_TOKEN and
        settings.BRIGHT_DATA_CUSTOMER_ID
    )
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "connected": db_healthy
            },
            "pixelrag": {
                "status": "healthy" if pixelrag_healthy else "not_initialized",
                "model": settings.PIXELRAG_MODEL,
                "device": settings.PIXELRAG_DEVICE
            },
            "bright_data": {
                "status": "configured" if bright_data_configured else "not_configured",
                "configured": bright_data_configured
            }
        },
        "config": {
            "vector_backend": settings.VECTOR_BACKEND,
            "storage_path": settings.STORAGE_PATH
        }
    }
