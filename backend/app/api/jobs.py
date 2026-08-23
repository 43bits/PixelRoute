"""
Job monitoring and results endpoints

Bright Data dataset endpoint behaviour:
  GET /dca/dataset?id=<snapshot_id>
  - Returns []          while still running
  - Returns [{...},...] when complete (the actual records)
  - Returns 400/404     on error
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime
from loguru import logger
from prisma import Json

from app.core.database import prisma, get_db
from app.services.bright_data import bright_data_service
from app.services.pixelrag import pixelrag_service

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _poll_and_update_job(job_id: str, bright_data_job_id: str) -> dict:
    """
    Poll Bright Data for the current job state and sync to DB.
    Returns the updated job record.
    """
    try:
        response = await bright_data_service.get_job_status(bright_data_job_id)

        # Bright Data returns:
        #   {"status": "running", "progress": 45}   while in progress
        #   [{...}, {...}]                           when complete (the records themselves)
        #   {"status": "failed", ...}               on failure

        if isinstance(response, list):
            # Job complete — records returned directly
            records = response
            items = len(records)
            new_status = "COMPLETED"
            progress = 100

            # Store results if not already stored
            existing = await prisma.scraperresult.count(where={"jobId": job_id})
            if existing == 0 and items > 0:
                job_rec = await prisma.scraperjob.find_unique(where={"id": job_id})
                if job_rec:
                    for item in records:
                        await prisma.scraperresult.create(
                            data={
                                "scraperId": job_rec.scraperId,
                                "jobId": job_id,
                                "url": item.get("url", ""),
                                "data": Json(item),
                                "metadata": Json({
                                    "title": str(item.get("title", "")),
                                    "timestamp": datetime.utcnow().isoformat(),
                                }),
                            }
                        )

            updated = await prisma.scraperjob.update(
                where={"id": job_id},
                data={
                    "status": new_status,
                    "progress": progress,
                    "itemsScraped": items,
                    "completedAt": datetime.utcnow(),
                    "duration": None,
                },
            )
            return updated

        elif isinstance(response, dict):
            raw_status = response.get("status", "running").lower()
            status_map = {
                "completed": "COMPLETED",
                "finished":  "COMPLETED",
                "ready":     "COMPLETED",
                "failed":    "FAILED",
                "error":     "FAILED",
                "running":   "RUNNING",
                "pending":   "PENDING",
                "initializing": "RUNNING",
            }
            new_status = status_map.get(raw_status, "RUNNING")
            progress   = int(response.get("progress", 0))
            items      = int(response.get("items_collected", response.get("records", 0)))

            update_data: dict = {
                "status":      new_status,
                "progress":    progress,
                "itemsScraped": items,
            }
            if new_status in ("COMPLETED", "FAILED"):
                update_data["completedAt"] = datetime.utcnow()
                if response.get("error"):
                    update_data["error"] = str(response["error"])

            updated = await prisma.scraperjob.update(
                where={"id": job_id},
                data=update_data,
            )
            return updated

    except Exception as e:
        logger.warning(f"Poll failed for job {job_id}: {e}")

    # Return current record unchanged on error
    return await prisma.scraperjob.find_unique(where={"id": job_id})


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/scraper/{scraper_id}")
async def list_scraper_jobs(
    scraper_id: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_db),
):
    """List jobs for a scraper"""
    jobs = await prisma.scraperjob.find_many(
        where={"scraperId": scraper_id},
        skip=skip,
        take=limit,
        order={"createdAt": "desc"},
    )
    total = await prisma.scraperjob.count(where={"scraperId": scraper_id})
    return {"jobs": jobs, "total": total, "skip": skip, "limit": limit}


@router.get("/{job_id}")
async def get_job_status(job_id: str, db=Depends(get_db)):
    """
    Get job status. If still RUNNING, polls Bright Data live and syncs DB.
    """
    job = await prisma.scraperjob.find_unique(
        where={"id": job_id},
        include={"scraper": True},
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Live-poll Bright Data while job is still running
    if job.status == "RUNNING" and job.brightDataJobId:
        job = await _poll_and_update_job(job_id, job.brightDataJobId)

    return {
        "id":           job.id,
        "scraperId":    job.scraperId,
        "status":       job.status,
        "progress":     job.progress,
        "urls":         job.urls,
        "itemsScraped": job.itemsScraped,
        "errorCount":   job.errorCount,
        "startedAt":    job.startedAt.isoformat() if job.startedAt else None,
        "completedAt":  job.completedAt.isoformat() if job.completedAt else None,
        "duration":     job.duration,
        "error":        job.error,
    }


@router.get("/{job_id}/results")
async def get_job_results(
    job_id: str,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db),
):
    """Get scraped results for a job"""
    job = await prisma.scraperjob.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = await prisma.scraperresult.find_many(
        where={"jobId": job_id},
        skip=skip,
        take=limit,
        order={"scrapedAt": "desc"},
    )
    total = await prisma.scraperresult.count(where={"jobId": job_id})

    return {"results": results, "total": total, "skip": skip, "limit": limit}


@router.post("/{job_id}/sync")
async def sync_job_results(
    job_id: str,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """Force-sync results from Bright Data right now"""
    job = await prisma.scraperjob.find_unique(
        where={"id": job_id},
        include={"scraper": True},
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.brightDataJobId:
        raise HTTPException(status_code=400, detail="No Bright Data job ID on this job")

    try:
        results = await bright_data_service.get_results(job.brightDataJobId)

        if results:
            background_tasks.add_task(
                _store_results_background,
                job_id=job.id,
                scraper_id=job.scraperId,
                results=results,
            )
            return {"success": True, "message": f"Syncing {len(results)} results", "count": len(results)}
        else:
            return {"success": True, "message": "No results yet — job may still be running", "count": 0}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync: {str(e)}")


async def _store_results_background(job_id: str, scraper_id: str, results: list):
    """Background task — store results and run PixelRAG"""
    stored = 0
    for item in results:
        try:
            url = item.get("url", "")
            result = await prisma.scraperresult.create(
                data={
                    "scraperId": scraper_id,
                    "jobId":     job_id,
                    "url":       url,
                    "data":      Json(item),
                    "metadata":  Json({
                        "title":     str(item.get("title", "")),
                        "timestamp": datetime.utcnow().isoformat(),
                    }),
                }
            )
            stored += 1

            # PixelRAG visual embedding (best-effort)
            if url:
                try:
                    visual = await pixelrag_service.process_scraper_result(
                        url=url,
                        scraper_id=scraper_id,
                        result_id=result.id,
                    )
                    await prisma.scraperresult.update(
                        where={"id": result.id},
                        data={
                            "screenshotUrl": visual["screenshot"]["tiles_dir"],
                            "tilesPath":     visual["screenshot"]["tiles_dir"],
                            "embeddingId":   f"{scraper_id}_{result.id}",
                        },
                    )
                except Exception as ve:
                    logger.warning(f"PixelRAG failed for {url}: {ve}")

        except Exception as e:
            logger.error(f"Failed to store result: {e}")
            await prisma.scraperjob.update(
                where={"id": job_id},
                data={"errorCount": {"increment": 1}},
            )

    await prisma.scraperjob.update(
        where={"id": job_id},
        data={
            "status":       "COMPLETED",
            "completedAt":  datetime.utcnow(),
            "itemsScraped": stored,
            "progress":     100,
        },
    )
    logger.success(f"Job {job_id}: stored {stored} results")
