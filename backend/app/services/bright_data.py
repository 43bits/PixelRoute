"""
Bright Data Scraper Studio API integration

Real API flow:
  1. Scrapers (collectors) are created in Bright Data UI/CLI → gives you a collector_id (c_xxxx)
  2. POST /dca/trigger?collector=<collector_id>  → returns collection_id (j_xxxx)
  3. GET  /dca/dataset?id=<collection_id>        → returns results when ready

There is NO API endpoint to programmatically create a collector.
Users must create one in Scraper Studio and paste the collector_id into our app.
"""

import aiohttp
import asyncio
import json
from typing import Any, List, Dict, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class BrightDataService:
    """Service for interacting with Bright Data Scraper Studio"""

    def __init__(self):
        self.api_url = settings.BRIGHT_DATA_API_URL  # https://api.brightdata.com
        self.api_token = settings.BRIGHT_DATA_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    # ── Scraper "creation" ────────────────────────────────────────────────────
    # Bright Data has no API endpoint to create a collector.
    # We store the user-supplied collector_id and validate it exists.

    async def validate_collector(self, collector_id: str) -> Dict[str, Any]:
        """
        Validate that a collector_id exists and is accessible.
        Tries a dry-run trigger with no URLs to confirm access.

        Returns basic info dict, raises on 401/404.
        """
        logger.info(f"Validating collector: {collector_id}")

        # Attempt to get collector info via a lightweight GET on /dca/dataset
        # (an empty snapshot check is the safest way to validate access)
        async with aiohttp.ClientSession() as session:
            try:
                # POST trigger with empty array — Bright Data returns 400/422 for
                # bad input but 401/404 for auth/not-found, which is what we want
                url = f"{self.api_url}/dca/trigger"
                params = {"collector": collector_id}
                async with session.post(
                    url,
                    json=[],
                    headers=self.headers,
                    params=params,
                ) as response:
                    # 400 / 422 = collector exists but input was empty (expected)
                    # 401 = bad token
                    # 404 = collector not found
                    if response.status in (400, 422):
                        logger.success(f"Collector {collector_id} is valid")
                        return {"collector_id": collector_id, "status": "valid"}
                    elif response.status == 401:
                        raise PermissionError("Invalid Bright Data API token")
                    elif response.status == 404:
                        raise ValueError(
                            f"Collector '{collector_id}' not found. "
                            "Create a scraper in Bright Data Scraper Studio first "
                            "and copy its collector ID (starts with c_)."
                        )
                    else:
                        response.raise_for_status()
                        return {"collector_id": collector_id, "status": "valid"}

            except aiohttp.ClientError as e:
                logger.error(f"Failed to validate collector: {e}")
                raise

    def register_scraper(
        self,
        collector_id: str,
        name: str,
        target_urls: List[str],
        fields: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        'Create' a scraper in our system by registering a Bright Data collector_id.
        No API call needed — the collector already exists in Bright Data.

        Returns a dict that maps to our Scraper model.
        """
        logger.info(f"Registering Bright Data collector '{collector_id}' as '{name}'")
        return {
            "collector_id": collector_id,
            "name": name,
            "description": description or f"Scraper for {', '.join(target_urls[:2])}",
            "target_urls": target_urls,
            "fields": self._format_fields(fields),
            "status": "ACTIVE",
        }

    def _format_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format field definitions (kept for internal use / display)"""
        formatted = []
        for field in fields:
            formatted_field = {
                "name": field["name"],
                "type": field.get("fieldType", "text").lower(),
                "description": field.get("description", ""),
            }
            if field.get("visualHints"):
                formatted_field["visual_context"] = field["visualHints"]
            if field.get("selector"):
                formatted_field["selector"] = field["selector"]
            formatted.append(formatted_field)
        return formatted

    # ── Trigger a run ─────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def trigger_scraper(
        self,
        collector_id: str,
        urls: List[str],
    ) -> Dict[str, Any]:
        """
        Trigger a batch scraping job.

        POST /dca/trigger?collector=<collector_id>
        Body: [{"url": "https://..."}, ...]

        Returns {"collection_id": "j_xxxx"} — use this as snapshot_id everywhere.
        """
        logger.info(f"Triggering collector {collector_id} for {len(urls)} URL(s)")

        payload = [{"url": url} for url in urls]

        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/trigger"
                params = {"collector": collector_id}

                async with session.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    params=params,
                ) as response:
                    if response.status == 404:
                        raise ValueError(
                            f"Collector '{collector_id}' not found on Bright Data. "
                            "Check that it's published (Active/Ready status) in Scraper Studio."
                        )
                    response.raise_for_status()
                    result = await response.json()

                    # Bright Data returns collection_id; alias as snapshot_id for consistency
                    collection_id = result.get("collection_id") or result.get("snapshot_id")
                    logger.success(f"Job triggered: collection_id={collection_id}")
                    return {"snapshot_id": collection_id, "collection_id": collection_id}

            except aiohttp.ClientError as e:
                logger.error(f"Failed to trigger scraper: {e}")
                raise

    # ── Job status ────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_job_status(self, snapshot_id: str) -> Any:
        """
        GET /dca/dataset?id=<snapshot_id>

        Bright Data returns application/jsonl — one JSON per line.
          ""           → still running
          1+ JSON lines → records (complete)
        """
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/dataset"
                params = {"id": snapshot_id}

                async with session.get(url, headers=self.headers, params=params) as response:
                    response.raise_for_status()
                    text = await response.text()

                    if not text or not text.strip():
                        return ""  # still running

                    records = []
                    for line in text.strip().splitlines():
                        line = line.strip()
                        if line:
                            try:
                                records.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass

                    if len(records) == 0:
                        return ""       # nothing parseable yet
                    if len(records) == 1:
                        return records[0]   # single dict
                    return records          # list of dicts

            except aiohttp.ClientError as e:
                logger.error(f"Failed to get job status: {e}")
                raise

    # ── Fetch results ─────────────────────────────────────────────────────────

    async def get_results(self, snapshot_id: str, format: str = "json") -> List[Dict[str, Any]]:
        """Parse JSONL and return list of records."""
        logger.info(f"Fetching results for snapshot {snapshot_id}")
        raw = await self.get_job_status(snapshot_id)
        if isinstance(raw, list):
            logger.success(f"Retrieved {len(raw)} records")
            return raw
        if isinstance(raw, dict):
            return [raw]
        return []

    # ── Poll until done ───────────────────────────────────────────────────────

    async def wait_for_completion(
        self,
        snapshot_id: str,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Poll until job completes or timeout."""
        logger.info(f"Polling job {snapshot_id}...")

        elapsed = 0
        while elapsed < timeout:
            status = await self.get_job_status(snapshot_id)

            job_status = status.get("status", "").lower()

            if job_status in ("completed", "finished", "ready"):
                logger.success(f"Job {snapshot_id} completed")
                return status
            elif job_status in ("failed", "error"):
                logger.error(f"Job {snapshot_id} failed")
                raise Exception(f"Job failed: {status.get('error', 'Unknown error')}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            if elapsed % 30 == 0:
                progress = status.get("progress", "?")
                logger.info(f"  job progress: {progress}%  ({elapsed}s elapsed)")

        raise TimeoutError(f"Job {snapshot_id} did not complete within {timeout}s")

    # ── Self-healing ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def trigger_self_heal(
        self,
        collector_id: str,
        prompt: str = "Fix broken selectors and update the scraper to work with the current page layout",
    ) -> Dict[str, Any]:
        """
        Trigger Bright Data's AI Self-Healing on an existing collector.

        POST /api/v1/ai/collector/<collector_id>/self_heal
        Body: {"prompt": "..."}

        Returns a job_id to poll via get_self_heal_status().
        """
        logger.info(f"Triggering self-heal for collector {collector_id}")

        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/api/v1/ai/collector/{collector_id}/self_heal"
                async with session.post(
                    url,
                    json={"prompt": prompt},
                    headers=self.headers,
                ) as response:
                    if response.status == 404:
                        # Self-heal API may not be available on all plans
                        logger.warning(
                            "Self-heal API returned 404 — feature may not be enabled on this plan. "
                            "Update the scraper manually in Bright Data Scraper Studio."
                        )
                        return {"status": "not_available", "collector_id": collector_id}
                    response.raise_for_status()
                    result = await response.json()
                    logger.success(f"Self-heal job started: {result}")
                    return result

            except aiohttp.ClientError as e:
                logger.error(f"Failed to trigger self-heal: {e}")
                raise


# Global service instance
bright_data_service = BrightDataService()
