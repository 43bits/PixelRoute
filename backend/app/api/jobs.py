"""
Job monitoring and results endpoints

Bright Data /dca/dataset response shapes:
  ""            -> still running (empty string)
  []            -> still running (empty list)  
  [{...}, ...]  -> complete, records as list
  {...}         -> complete, single record as dict
  {"status": "failed"} -> failed
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime
from loguru import logger
from prisma import Json

from app.core.database import prisma, get_db
from app.services.bright_data import bright_data_service
from app.services.pixelrag import pixelrag_service

router = APIRouter()


def _is_data_record(obj: dict) -> bool:
    """True if the dict looks like a scraped record rather than a status response."""
    status_keys = {"status", "progress", "error", "message"}
    data_keys   = {"title", "ASIN", "asin", "url", "price", "name", "image",
                   "rating", "description", "input"}
    return bool(data_keys & obj.keys()) and not (status_keys >= obj.keys())


async def _store_records(job_id: str, scraper_id: str, records: list):
    """Persist scraped records and update the job to COMPLETED."""
    existing = await prisma.scraperresult.count(where={"jobId": job_id})
    stored = existing

    if existing == 0:
        for item in records:
            try:
                await prisma.scraperresult.create(
                    data={
                        "scraperId": scraper_id,
                        "jobId":     job_id,
                        "url":       str(item.get("url") or item.get("input", {}).get("url", "")),
                        "data":      Json(item),
                        "metadata":  Json({
                            "title":     str(item.get("title", "")),
                            "asin":      str(item.get("ASIN", item.get("asin", ""))),
                            "timestamp": datetime.utcnow().isoformat(),
                        }),
                    }
                )
                stored += 1
            except Exception as e:
                logger.error(f"Failed to store record: {e}")

    await prisma.scraperjob.update(
        where={"id": job_id},
        data={
            "status":       "COMPLETED",
            "progress":     100,
            "itemsScraped": stored,
            "completedAt":  datetime.utcnow(),
        },
    )
    logger.success(f"Job {job_id}: stored {stored} records")


async def _poll_and_update_job(job_id: str, bright_data_job_id: str):
    """
    Call Bright Data, parse response, update DB.
    Returns the (possibly updated) job record.
    """
    try:
        response = await bright_data_service.get_job_status(bright_data_job_id)

        # ── Still running (empty string or empty list) ───────────────────────
        if response is None or response == "" or response == []:
            # If job has been running > 10 minutes, mark as failed
            job_rec = await prisma.scraperjob.find_unique(where={"id": job_id})
            if job_rec and job_rec.startedAt:
                elapsed = (datetime.utcnow() - job_rec.startedAt.replace(tzinfo=None)).total_seconds()
                if elapsed > 600:  # 10 minutes
                    logger.warning(f"Job {job_id} timed out after {elapsed:.0f}s — marking FAILED")
                    return await prisma.scraperjob.update(
                        where={"id": job_id},
                        data={"status": "FAILED", "completedAt": datetime.utcnow(),
                              "error": "No data returned from Bright Data (timeout)"},
                    )
            return job_rec

        # ── List of records ─────────────────────────────────────────────────
        if isinstance(response, list) and len(response) > 0:
            job_rec = await prisma.scraperjob.find_unique(where={"id": job_id})
            await _store_records(job_id, job_rec.scraperId, response)
            return await prisma.scraperjob.find_unique(where={"id": job_id})

        # ── Single record dict ──────────────────────────────────────────────
        if isinstance(response, dict) and _is_data_record(response):
            job_rec = await prisma.scraperjob.find_unique(where={"id": job_id})
            await _store_records(job_id, job_rec.scraperId, [response])
            return await prisma.scraperjob.find_unique(where={"id": job_id})

        # ── Status dict ─────────────────────────────────────────────────────
        if isinstance(response, dict):
            raw = response.get("status", "running").lower()
            status_map = {
                "completed":    "COMPLETED",
                "finished":     "COMPLETED",
                "ready":        "COMPLETED",
                "failed":       "FAILED",
                "error":        "FAILED",
                "running":      "RUNNING",
                "pending":      "PENDING",
                "initializing": "RUNNING",
            }
            new_status = status_map.get(raw, "RUNNING")
            progress   = int(response.get("progress", 0))
            items      = int(response.get("items_collected", response.get("records", 0)))

            update: dict = {"status": new_status, "progress": progress, "itemsScraped": items}
            if new_status in ("COMPLETED", "FAILED"):
                update["completedAt"] = datetime.utcnow()
                if response.get("error"):
                    update["error"] = str(response["error"])

            return await prisma.scraperjob.update(where={"id": job_id}, data=update)

    except Exception as e:
        logger.warning(f"Poll error for job {job_id}: {e}")

    return await prisma.scraperjob.find_unique(where={"id": job_id})


# ── Routes ──────────────────────────────────────────────────────────────────────

@router.get("/scraper/{scraper_id}")
async def list_scraper_jobs(
    scraper_id: str,
    skip: int = 0,
    limit: int = 20,
    db=Depends(get_db),
):
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
    """Get job status — auto-polls Bright Data when RUNNING."""
    job = await prisma.scraperjob.find_unique(
        where={"id": job_id},
        include={"scraper": True},
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
    job = await prisma.scraperjob.find_unique(where={"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.brightDataJobId:
        raise HTTPException(status_code=400, detail="No Bright Data job ID")

    try:
        results = await bright_data_service.get_results(job.brightDataJobId)
        if results:
            background_tasks.add_task(_store_results_background, job.id, job.scraperId, results)
            return {"success": True, "message": f"Syncing {len(results)} results", "count": len(results)}
        return {"success": True, "message": "No results yet", "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _store_results_background(job_id: str, scraper_id: str, results: list):
    await _store_records(job_id, scraper_id, results)
