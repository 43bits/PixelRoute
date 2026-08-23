"""
Scraper management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import traceback
from loguru import logger
from prisma import Json

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
    collectorId: Optional[str] = Field(
        None,
        description="Bright Data collector ID (c_xxxx) from Scraper Studio. "
                    "Leave blank to save as DRAFT and add later."
    )


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
    """
    Create a new scraper.

    If collectorId is provided, it is validated against Bright Data and the
    scraper is saved as ACTIVE. Without a collectorId it saves as DRAFT —
    you can add the collector ID later via PATCH /{id}.

    NOTE: Bright Data has no API to create collectors programmatically.
    Create one in Scraper Studio (https://brightdata.com/cp/scrapers),
    publish it, and copy the ID (starts with c_).
    """
    try:
        collector_id = request.collectorId

        # If a collector ID was supplied, register it (no API call needed to create)
        if collector_id:
            bright_data_service.register_scraper(
                collector_id=collector_id,
                name=request.name,
                target_urls=request.targetUrls,
                fields=[field.model_dump() for field in request.fields],
                description=request.description,
            )
            status = "ACTIVE"
        else:
            status = "DRAFT"

        # Save to database
        scraper = await prisma.scraper.create(
            data={
                "name": request.name,
                "description": request.description,
                "brightDataScraperId": collector_id,
                "targetUrls": request.targetUrls,
                "status": status,
                "autoHeal": request.autoHeal,
                "fields": {
                    "create": [
                        {
                            "name": field.name,
                            "description": field.description,
                            "fieldType": field.fieldType,
                            "selector": field.selector,
                            "visualHints": Json(field.visualHints if field.visualHints else {}),
                            "isRequired": field.isRequired,
                        }
                        for field in request.fields
                    ]
                },
            },
            include={"fields": True},
        )

        return scraper

    except Exception as e:
        logger.error(f"create_scraper error: {traceback.format_exc()}")
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
        job = await prisma.scraperjob.create(
            data={
                "scraperId": scraper_id,
                "brightDataJobId": job_result.get("snapshot_id"),
                "urls": urls,
                "status": "RUNNING",
                "startedAt": datetime.utcnow(),
            }
        )
        
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
        # Trigger self-heal in Bright Data
        heal_result = await bright_data_service.trigger_self_heal(scraper.brightDataScraperId)

        # Update database
        updated = await prisma.scraper.update(
            where={"id": scraper_id},
            data={
                "lastHealed": datetime.utcnow(),
                "healCount": scraper.healCount + 1,
            },
        )

        return {
            "success": True,
            "healCount": updated.healCount,
            "lastHealed": updated.lastHealed.isoformat(),
            "brightDataStatus": heal_result.get("status"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self-healing failed: {str(e)}")
