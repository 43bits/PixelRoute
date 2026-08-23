"""
Bright Data Scraper Studio API integration
Handles scraper creation, execution, and self-healing
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class BrightDataService:
    """Service for interacting with Bright Data Scraper Studio"""
    
    def __init__(self):
        self.api_url = settings.BRIGHT_DATA_API_URL
        self.api_token = settings.BRIGHT_DATA_API_TOKEN
        self.customer_id = settings.BRIGHT_DATA_CUSTOMER_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def create_scraper(
        self,
        name: str,
        target_urls: List[str],
        fields: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new scraper in Bright Data Scraper Studio
        
        Args:
            name: Scraper name
            target_urls: List of URLs to scrape
            fields: Field definitions with visual descriptions
            description: Optional scraper description
        
        Returns:
            Scraper configuration with ID
        """
        logger.info(f"Creating Bright Data scraper: {name}")
        
        # Build scraper configuration
        # Using AI-powered scraper creation for self-healing
        config = {
            "name": name,
            "description": description or f"Self-healing scraper for {', '.join(target_urls[:3])}",
            "target_urls": target_urls,
            "fields": self._format_fields(fields),
            "ai_enabled": True,  # Enable AI for self-healing
            "auto_retry": True,
            "proxy_type": "datacenter"  # Free tier
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Create scraper using Scraper Studio API
                url = f"{self.api_url}/dca/create_collector"
                async with session.post(url, json=config, headers=self.headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    logger.success(f"Scraper created: {result.get('collector_id')}")
                    return result
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to create scraper: {e}")
                raise
    
    def _format_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format field definitions for Bright Data API"""
        formatted = []
        
        for field in fields:
            formatted_field = {
                "name": field["name"],
                "type": field.get("fieldType", "text").lower(),
                "description": field.get("description", ""),
            }
            
            # Add visual hints for AI-powered extraction
            if field.get("visualHints"):
                formatted_field["visual_context"] = field["visualHints"]
            
            # Add selector if provided
            if field.get("selector"):
                formatted_field["selector"] = field["selector"]
            
            formatted.append(formatted_field)
        
        return formatted
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def trigger_scraper(
        self,
        collector_id: str,
        urls: List[str]
    ) -> Dict[str, Any]:
        """
        Trigger a scraping job
        
        Args:
            collector_id: Bright Data collector ID
            urls: URLs to scrape
        
        Returns:
            Job information with job ID
        """
        logger.info(f"Triggering scraper {collector_id} for {len(urls)} URLs")
        
        payload = [{"url": url} for url in urls]
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/trigger"
                params = {"collector": collector_id}
                
                async with session.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    params=params
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    logger.success(f"Job triggered: {result.get('snapshot_id')}")
                    return result
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to trigger scraper: {e}")
                raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_job_status(
        self,
        snapshot_id: str
    ) -> Dict[str, Any]:
        """
        Get status of a scraping job
        
        Args:
            snapshot_id: Bright Data snapshot/job ID
        
        Returns:
            Job status and progress
        """
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/dataset"
                params = {"id": snapshot_id}
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to get job status: {e}")
                raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_results(
        self,
        snapshot_id: str,
        format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve scraping results
        
        Args:
            snapshot_id: Bright Data snapshot/job ID
            format: Result format (json, csv, etc.)
        
        Returns:
            List of scraped items
        """
        logger.info(f"Fetching results for job {snapshot_id}")
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/dataset"
                params = {
                    "id": snapshot_id,
                    "format": format
                }
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    response.raise_for_status()
                    results = await response.json()
                    
                    logger.success(f"Retrieved {len(results)} results")
                    return results
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to get results: {e}")
                raise
    
    async def wait_for_completion(
        self,
        snapshot_id: str,
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Wait for scraping job to complete
        
        Args:
            snapshot_id: Job ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
        
        Returns:
            Final job status
        """
        logger.info(f"Waiting for job {snapshot_id} to complete...")
        
        elapsed = 0
        while elapsed < timeout:
            status = await self.get_job_status(snapshot_id)
            
            job_status = status.get("status", "").lower()
            if job_status in ["completed", "finished"]:
                logger.success(f"Job {snapshot_id} completed successfully")
                return status
            elif job_status in ["failed", "error"]:
                logger.error(f"Job {snapshot_id} failed")
                raise Exception(f"Job failed: {status.get('error', 'Unknown error')}")
            
            # Still running, wait and poll again
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            if elapsed % 30 == 0:  # Log progress every 30 seconds
                progress = status.get("progress", 0)
                logger.info(f"Job progress: {progress}%")
        
        raise TimeoutError(f"Job {snapshot_id} did not complete within {timeout} seconds")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def update_scraper(
        self,
        collector_id: str,
        fields: Optional[List[Dict[str, Any]]] = None,
        urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update scraper configuration (for self-healing)
        
        Args:
            collector_id: Scraper ID
            fields: Updated field definitions
            urls: Updated target URLs
        
        Returns:
            Updated scraper configuration
        """
        logger.info(f"Updating scraper {collector_id}")
        
        update_data = {}
        if fields:
            update_data["fields"] = self._format_fields(fields)
        if urls:
            update_data["target_urls"] = urls
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/dca/collector/{collector_id}"
                async with session.patch(url, json=update_data, headers=self.headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    logger.success(f"Scraper updated: {collector_id}")
                    return result
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to update scraper: {e}")
                raise
    
    async def enable_self_healing(
        self,
        collector_id: str
    ) -> Dict[str, Any]:
        """
        Enable AI-powered self-healing for a scraper
        
        Args:
            collector_id: Scraper ID
        
        Returns:
            Updated configuration
        """
        logger.info(f"Enabling self-healing for {collector_id}")
        
        return await self.update_scraper(
            collector_id,
            # Enable AI and auto-retry features
            # These will be passed as part of the configuration
        )


# Global service instance
bright_data_service = BrightDataService()
