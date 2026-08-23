"""
Job monitoring and results endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime

from app.core.database import prisma, get_db
from app.services.bright_data import bright_data_service
from app.services.pixelrag import pixelrag_service

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(job_id: str, db = Depends(get_db)):
    """Get job status and progress"""
    
    job = await prisma.scraperjob.find_unique(
        where={"id": job_id},
        include={"scraper": True}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get live status from Bright Data if job is still running
    if job.status == "RUNNING" and job.brightDataJobId:
        try:
            bd_status = await bright_data_service.get_job_status(job.brightDataJobId)
            
            # Update job status in database
            status_map = {
                "completed": "COMPLETED",
                "finished": "COMPLETED",
                "failed": "FAILED",
                "error": "FAILED",
                "running": "RUNNING",
                "pending": "PENDING"
            }
            
            new_status = status_map.get(bd_status.get("status", "").lower(), "RUNNING")
            progress = bd_status.get("progress", job.progress)
            
            if new_status != job.status or progress != job.progress:
                job = await prisma.scraperjob.update(
                    where={"id": job_id},
                    data={
                        "status": new_status,
                        "progress": progress,
                        "itemsScraped": bd_status.get("items_collected", job.itemsScraped),
                        "completedAt": datetime.utcnow() if new_status in ["COMPLETED", "FAILED"] else None
                    }
                )
        except Exception as e:
            print(f"Warning: Failed to get live status from Bright Data: {e}")
    
    return {
        "id": job.id,
        "scraperId": job.scraperId,
        "status": job.status,
        "progress": job.progress,
        "urls": job.urls,
        "itemsScraped": job.itemsScraped,
        "errorCount": job.errorCount,
        "startedAt": job.startedAt.isoformat() if job.startedAt else None,
        "completedAt": job.completedAt.isoformat() if job.completedAt else None,
        "duration": job.duration,
        "error": job.error
    }


@router.get("/{job_id}/results")
async def get_job_results(
    job_id: str,
    skip: int = 0,
    limit: int = 50,
    db = Depends(get_db)
):
    """Get scraped results for a job"""
    
    job = await prisma.scraperjob.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get results from database
    results = await prisma.scraperresult.find_many(
        where={"jobId": job_id},
        skip=skip,
        take=limit,
        order={"scrapedAt": "desc"}
    )
    
    total = await prisma.scraperresult.count(where={"jobId": job_id})
    
    return {
        "results": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/{job_id}/sync")
async def sync_job_results(
    job_id: str,
    background_tasks: BackgroundTasks,
    db = Depends(get_db)
):
    """Sync results from Bright Data and process with PixelRAG"""
    
    job = await prisma.scraperjob.find_unique(
        where={"id": job_id},
        include={"scraper": True}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.brightDataJobId:
        raise HTTPException(status_code=400, detail="No Bright Data job ID")
    
    try:
        # Get results from Bright Data
        bd_results = await bright_data_service.get_results(job.brightDataJobId)
        
        # Process results in background
        background_tasks.add_task(
            process_and_store_results,
            job_id=job.id,
            scraper_id=job.scraperId,
            results=bd_results
        )
        
        return {
            "success": True,
            "message": f"Syncing {len(bd_results)} results",
            "count": len(bd_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync results: {str(e)}")


async def process_and_store_results(
    job_id: str,
    scraper_id: str,
    results: list
):
    """Background task to process and store results"""
    
    for item in results:
        try:
            url = item.get("url", "")
            data = item
            
            # Create result record
            result = await prisma.scraperresult.create({
                "scraperId": scraper_id,
                "jobId": job_id,
                "url": url,
                "data": data,
                "metadata": {
                    "title": item.get("title", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
            # Process with PixelRAG if URL is available
            if url:
                try:
                    visual_data = await pixelrag_service.process_scraper_result(
                        url=url,
                        scraper_id=scraper_id,
                        result_id=result.id
                    )
                    
                    # Update result with visual data
                    await prisma.scraperresult.update(
                        where={"id": result.id},
                        data={
                            "screenshotUrl": visual_data["screenshot"]["tiles_dir"],
                            "tilesPath": visual_data["screenshot"]["tiles_dir"],
                            "embeddingId": f"{scraper_id}_{result.id}"
                        }
                    )
                    
                except Exception as e:
                    print(f"Warning: Failed to process visual data for {url}: {e}")
            
        except Exception as e:
            print(f"Error processing result: {e}")
            
            # Update error count
            await prisma.scraperjob.update(
                where={"id": job_id},
                data={"errorCount": {"increment": 1}}
            )
    
    # Mark job as completed
    await prisma.scraperjob.update(
        where={"id": job_id},
        data={
            "status": "COMPLETED",
            "completedAt": datetime.utcnow(),
            "itemsScraped": len(results)
        }
    )


@router.get("/scraper/{scraper_id}")
async def list_scraper_jobs(
    scraper_id: str,
    skip: int = 0,
    limit: int = 20,
    db = Depends(get_db)
):
    """List jobs for a scraper"""
    
    jobs = await prisma.scraperjob.find_many(
        where={"scraperId": scraper_id},
        skip=skip,
        take=limit,
        order={"createdAt": "desc"}
    )
    
    total = await prisma.scraperjob.count(where={"scraperId": scraper_id})
    
    return {
        "jobs": jobs,
        "total": total,
        "skip": skip,
        "limit": limit
    }
