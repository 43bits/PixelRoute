"""
Scraper management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import prisma, get_db
from app.services.bright_data import bright_data_service
from app.services.pixelrag import pixelrag_service

router = APIRouter()


# Request/Response models
class FieldDefinition(BaseModel):
    name: str = Field(..., description="Field name")
    description: str = Field(..., description="Plain language description for visual identification")
    fieldType: str = Field(default="TEXT", description="Field type: TEXT, NUMBER, URL, IMAGE, DATE, VISUAL")
    selector: Optional[str] = Field(None, description="CSS selector (optional)")
    visualHints: Optional[dict] = Field(None, description="Visual characteristics")
    isRequired: bool = Field(default=False)


class CreateScraperRequest(BaseModel):
    name: str = Field(..., description="Scraper name")
    description: Optional[str] = Field(None, description="Scraper description")
    targetUrls: List[str] = Field(..., description="URLs to scrape")
    fields: List[FieldDefinition] = Field(..., description="Fields to extract")
    autoHeal: bool = Field(default=True, description="Enable self-healing")


class UpdateScraperRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    targetUrls: Optional[List[str]] = None
    fields: Optional[List[FieldDefinition]] = None
    isActive: Optional[bool] = None
    autoHeal: Optional[bool] = None


class RunScraperRequest(BaseModel):
    urls: Optional[List[str]] = Field(None, description="URLs to scrape (uses targetUrls if not provided)")


@router.post("/")
async def create_scraper(request: CreateScraperRequest, db = Depends(get_db)):
    """Create a new scraper"""
    
    try:
        # Create scraper in Bright Data
        bright_data_result = await bright_data_service.create_scraper(
            name=request.name,
            target_urls=request.targetUrls,
            fields=[field.model_dump() for field in request.fields],
            description=request.description
        )
        
        # Create in database
        scraper = await prisma.scraper.create({
            "name": request.name,
            "description": request.description,
            "brightDataScraperId": bright_data_result.get("collector_id"),
            "targetUrls": request.targetUrls,
            "status": "ACTIVE" if bright_data_result.get("collector_id") else "DRAFT",
            "autoHeal": request.autoHeal,
            "fields": {
                "create": [
                    {
                        "name": field.name,
                        "description": field.description,
                        "fieldType": field.fieldType,
                        "selector": field.selector,
                        "visualHints": field.visualHints or {},
                        "isRequired": field.isRequired
                    }
                    for field in request.fields
                ]
            }
        })
        
        return {
            "id": scraper.id,
            "name": scraper.name,
            "status": scraper.status,
            "brightDataScraperId": scraper.brightDataScraperId,
            "createdAt": scraper.createdAt.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scraper: {str(e)}")


@router.get("/")
async def list_scrapers(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db = Depends(get_db)
):
    """List all scrapers"""
    
    where = {}
    if status:
        where["status"] = status
    
    scrapers = await prisma.scraper.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"},
        include={"fields": True}
    )
    
    total = await prisma.scraper.count(where=where)
    
    return {
        "scrapers": scrapers,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{scraper_id}")
async def get_scraper(scraper_id: str, db = Depends(get_db)):
    """Get scraper details"""
    
    scraper = await prisma.scraper.find_unique(
        where={"id": scraper_id},
        include={
            "fields": True,
            "jobs": {
                "take": 10,
                "order_by": {"createdAt": "desc"}
            }
        }
    )
    
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    return scraper


@router.patch("/{scraper_id}")
async def update_scraper(
    scraper_id: str,
    request: UpdateScraperRequest,
    db = Depends(get_db)
):
    """Update scraper configuration"""
    
    # Check if scraper exists
    scraper = await prisma.scraper.find_unique(where={"id": scraper_id})
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    # Build update data
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.targetUrls is not None:
        update_data["targetUrls"] = request.targetUrls
    if request.isActive is not None:
        update_data["isActive"] = request.isActive
    if request.autoHeal is not None:
        update_data["autoHeal"] = request.autoHeal
    
    # Update in database
    updated_scraper = await prisma.scraper.update(
        where={"id": scraper_id},
        data=update_data
    )
    
    # Update in Bright Data if needed
    if scraper.brightDataScraperId and (request.fields or request.targetUrls):
        try:
            await bright_data_service.update_scraper(
                scraper.brightDataScraperId,
                fields=[field.model_dump() for field in request.fields] if request.fields else None,
                urls=request.targetUrls
            )
        except Exception as e:
            # Log but don't fail
            print(f"Warning: Failed to update Bright Data scraper: {e}")
    
    return updated_scraper


@router.delete("/{scraper_id}")
async def delete_scraper(scraper_id: str, db = Depends(get_db)):
    """Delete a scraper"""
    
    scraper = await prisma.scraper.find_unique(where={"id": scraper_id})
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    # Delete from database (cascade will handle related records)
    await prisma.scraper.delete(where={"id": scraper_id})
    
    # Note: Not deleting from Bright Data to preserve historical data
    
    return {"success": True, "message": "Scraper deleted"}


@router.post("/{scraper_id}/run")
async def run_scraper(
    scraper_id: str,
    request: RunScraperRequest,
    db = Depends(get_db)
):
    """Trigger a scraping job"""
    
    # Get scraper
    scraper = await prisma.scraper.find_unique(where={"id": scraper_id})
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    if not scraper.brightDataScraperId:
        raise HTTPException(status_code=400, detail="Scraper not configured in Bright Data")
    
    # Determine URLs to scrape
    urls = request.urls or scraper.targetUrls
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    try:
        # Trigger job in Bright Data
        job_result = await bright_data_service.trigger_scraper(
            scraper.brightDataScraperId,
            urls
        )
        
        # Create job record
        job = await prisma.scraperjob.create({
            "scraperId": scraper_id,
            "brightDataJobId": job_result.get("snapshot_id"),
            "urls": urls,
            "status": "RUNNING",
            "startedAt": datetime.utcnow()
        })
        
        return {
            "jobId": job.id,
            "status": job.status,
            "urls": urls,
            "startedAt": job.startedAt.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scraping job: {str(e)}")


@router.post("/{scraper_id}/heal")
async def trigger_self_heal(scraper_id: str, db = Depends(get_db)):
    """Manually trigger self-healing for a scraper"""
    
    scraper = await prisma.scraper.find_unique(where={"id": scraper_id})
    if not scraper:
        raise HTTPException(status_code=404, detail="Scraper not found")
    
    if not scraper.brightDataScraperId:
        raise HTTPException(status_code=400, detail="Scraper not configured in Bright Data")
    
    try:
        # Enable self-healing in Bright Data
        await bright_data_service.enable_self_healing(scraper.brightDataScraperId)
        
        # Update database
        updated = await prisma.scraper.update(
            where={"id": scraper_id},
            data={
                "lastHealed": datetime.utcnow(),
                "healCount": scraper.healCount + 1
            }
        )
        
        return {
            "success": True,
            "healCount": updated.healCount,
            "lastHealed": updated.lastHealed.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing failed: {str(e)}")
