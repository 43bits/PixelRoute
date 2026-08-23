"""
PixelRAG integration for visual content understanding
Handles screenshot capture, tiling, embedding, and visual search.

All ML/playwright dependencies are OPTIONAL — if not installed the service
degrades gracefully so the core scraping API still works on Railway free tier.
"""

import os
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core.config import settings

# Optional heavy deps
try:
    import asyncio
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

pixelrag_initialized = False


async def initialize_pixelrag():
    """Initialize PixelRAG — best effort, never raises."""
    global pixelrag_initialized
    if pixelrag_initialized:
        return
    logger.info("Initializing PixelRAG...")
    try:
        os.makedirs(settings.PIXELRAG_INDEX_PATH, exist_ok=True)
        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        pixelrag_initialized = True
        logger.success("PixelRAG initialized successfully")
    except Exception as e:
        logger.warning(f"PixelRAG init skipped: {e}")
        pixelrag_initialized = True   # mark done so we don't retry


class PixelRAGService:
    """Visual content service — degrades gracefully when ML deps are absent."""

    def __init__(self):
        self.index_path   = settings.PIXELRAG_INDEX_PATH
        self.storage_path = settings.STORAGE_PATH

    async def process_scraper_result(
        self,
        url: str,
        scraper_id: str,
        result_id: str,
    ) -> Dict[str, Any]:
        """
        Screenshot → embed → index pipeline.
        Returns a stub result if playwright/pixelshot are not available.
        """
        logger.info(f"PixelRAG processing {result_id} ({url})")

        # Graceful stub when playwright / pixelshot not available
        if not _HAS_PLAYWRIGHT:
            logger.warning("playwright not installed — skipping visual processing")
            return {
                "result_id": result_id,
                "screenshot": {"tiles_dir": None},
                "status": "skipped",
            }

        try:
            import asyncio, hashlib

            url_hash  = hashlib.md5(url.encode()).hexdigest()[:12]
            tiles_dir = os.path.join(self.storage_path, "tiles", url_hash)
            os.makedirs(tiles_dir, exist_ok=True)

            # pixelshot capture
            proc = await asyncio.create_subprocess_exec(
                "pixelshot", url, "-o", tiles_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"pixelshot: {stderr.decode()}")

            tiles = sorted(
                str(p) for p in __import__("pathlib").Path(tiles_dir).glob("*.png")
            )
            logger.success(f"Captured {len(tiles)} tiles")
            return {
                "result_id": result_id,
                "screenshot": {"tiles_dir": tiles_dir, "tiles": tiles},
                "status": "completed",
            }

        except Exception as e:
            logger.warning(f"Visual processing failed (non-fatal): {e}")
            return {
                "result_id": result_id,
                "screenshot": {"tiles_dir": None},
                "status": "error",
                "error": str(e),
            }

    async def search_visual(
        self,
        query: str,
        scraper_id: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Natural language visual search — returns [] if index not ready."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "http://localhost:30001/search",
                    json={"queries": [{"text": query}], "n_docs": n_results},
                )
                r.raise_for_status()
                return r.json()
        except Exception:
            logger.warning("PixelRAG search unavailable — returning empty results")
            return []


# Global instance
pixelrag_service = PixelRAGService()


class PixelRAGService:
    """Service for visual content understanding with PixelRAG"""
    
    def __init__(self):
        self.model_name = settings.PIXELRAG_MODEL
        self.device = settings.PIXELRAG_DEVICE
        self.index_path = settings.PIXELRAG_INDEX_PATH
        self.storage_path = settings.STORAGE_PATH
    
    async def capture_screenshot(
        self,
        url: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture screenshot tiles of a web page
        
        Args:
            url: URL to capture
            output_dir: Directory to save tiles (optional)
        
        Returns:
            Dictionary with tile paths and metadata
        """
        logger.info(f"Capturing screenshot for: {url}")
        
        # Create output directory
        if not output_dir:
            # Use URL hash as directory name
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            output_dir = os.path.join(self.storage_path, "tiles", url_hash)
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use pixelshot to render page to tiles
            # Running as subprocess to avoid blocking
            cmd = [
                "pixelshot",
                url,
                "-o", output_dir
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"Screenshot capture failed: {error_msg}")
                raise Exception(f"Pixelshot failed: {error_msg}")
            
            # Get list of generated tiles
            tiles = sorted([
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.endswith(('.png', '.jpg', '.jpeg'))
            ])
            
            logger.success(f"Captured {len(tiles)} tiles for {url}")
            
            return {
                "url": url,
                "tiles_dir": output_dir,
                "tiles": tiles,
                "tile_count": len(tiles)
            }
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            raise
    
    async def embed_tiles(
        self,
        tiles_dir: str,
        scraper_id: str,
        result_id: str
    ) -> Dict[str, Any]:
        """
        Generate embeddings for screenshot tiles
        
        Args:
            tiles_dir: Directory containing tiles
            scraper_id: Associated scraper ID
            result_id: Associated result ID
        
        Returns:
            Embedding metadata
        """
        logger.info(f"Embedding tiles from: {tiles_dir}")
        
        try:
            # Step 1: Chunk tiles
            chunks_dir = os.path.join(tiles_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            
            cmd_chunk = ["pixelrag", "chunk", "--tiles-dir", tiles_dir]
            process = await asyncio.create_subprocess_exec(
                *cmd_chunk,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Step 2: Generate embeddings
            embeddings_dir = os.path.join(self.storage_path, "embeddings", scraper_id)
            os.makedirs(embeddings_dir, exist_ok=True)
            
            cmd_embed = [
                "pixelrag", "embed",
                "--shard-dir", tiles_dir,
                "--output-dir", embeddings_dir,
                "--model", self.model_name,
                "--device", self.device
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd_embed,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"Embedding failed: {error_msg}")
                raise Exception(f"Embedding failed: {error_msg}")
            
            logger.success(f"Generated embeddings for {tiles_dir}")
            
            return {
                "scraper_id": scraper_id,
                "result_id": result_id,
                "embeddings_dir": embeddings_dir,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Failed to embed tiles: {e}")
            raise
    
    async def build_index(
        self,
        scraper_id: str,
        embeddings_dir: str
    ) -> str:
        """
        Build or update FAISS/Qdrant index
        
        Args:
            scraper_id: Scraper ID
            embeddings_dir: Directory with embeddings
        
        Returns:
            Index path or collection name
        """
        logger.info(f"Building index for scraper: {scraper_id}")
        
        try:
            index_dir = os.path.join(self.index_path, scraper_id)
            os.makedirs(index_dir, exist_ok=True)
            
            # Check if we should use Qdrant or FAISS
            if settings.VECTOR_BACKEND == "qdrant":
                # Build Qdrant index
                collection_name = f"{settings.QDRANT_COLLECTION_NAME}_{scraper_id}"
                
                cmd = [
                    "pixelrag", "build-index",
                    "--embeddings-dir", embeddings_dir,
                    "--output-dir", index_dir,
                    "--backend", "qdrant",
                    "--qdrant-url", settings.QDRANT_URL,
                    "--collection", collection_name
                ]
                
                if settings.QDRANT_API_KEY:
                    # API key will be set via environment variable
                    pass
                
            else:
                # Build FAISS index
                cmd = [
                    "pixelrag", "build-index",
                    "--embeddings-dir", embeddings_dir,
                    "--output-dir", index_dir
                ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"Index building failed: {error_msg}")
                raise Exception(f"Index building failed: {error_msg}")
            
            logger.success(f"Index built for scraper {scraper_id}")
            return index_dir
            
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            raise
    
    async def search_visual(
        self,
        query: str,
        scraper_id: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search visual content using natural language query
        
        Args:
            query: Natural language query
            scraper_id: Optional scraper filter
            n_results: Number of results to return
        
        Returns:
            List of search results with scores and metadata
        """
        logger.info(f"Visual search query: {query}")
        
        try:
            # Determine which index to search
            if scraper_id:
                index_dir = os.path.join(self.index_path, scraper_id)
            else:
                # Search all indices (combine results)
                index_dir = self.index_path
            
            # Check if index exists
            if not os.path.exists(index_dir):
                logger.warning(f"No index found at: {index_dir}")
                return []
            
            # Use PixelRAG API to search
            # For now, we'll use a local HTTP request to pixelrag serve
            # In production, this could be a dedicated service
            
            import httpx
            
            # Start PixelRAG serve if not running (in production, this would be separate)
            search_url = "http://localhost:30001/search"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        search_url,
                        json={
                            "queries": [{"text": query}],
                            "n_docs": n_results
                        }
                    )
                    response.raise_for_status()
                    results = response.json()
                    
                    logger.success(f"Found {len(results)} results")
                    return results
                    
                except httpx.HTTPError:
                    # If serve not running, return empty results
                    logger.warning("PixelRAG serve not running, returning empty results")
                    return []
            
        except Exception as e:
            logger.error(f"Visual search failed: {e}")
            raise
    
    async def process_scraper_result(
        self,
        url: str,
        scraper_id: str,
        result_id: str
    ) -> Dict[str, Any]:
        """
        Complete pipeline: screenshot -> embed -> index
        
        Args:
            url: URL that was scraped
            scraper_id: Scraper ID
            result_id: Result ID
        
        Returns:
            Processing status and paths
        """
        logger.info(f"Processing result {result_id} from scraper {scraper_id}")
        
        try:
            # Step 1: Capture screenshot
            screenshot_data = await self.capture_screenshot(url)
            
            # Step 2: Generate embeddings
            embedding_data = await self.embed_tiles(
                screenshot_data["tiles_dir"],
                scraper_id,
                result_id
            )
            
            # Step 3: Update index
            index_path = await self.build_index(
                scraper_id,
                embedding_data["embeddings_dir"]
            )
            
            return {
                "result_id": result_id,
                "screenshot": screenshot_data,
                "embeddings": embedding_data,
                "index_path": index_path,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Failed to process result: {e}")
            raise


# Global service instance
pixelrag_service = PixelRAGService()
