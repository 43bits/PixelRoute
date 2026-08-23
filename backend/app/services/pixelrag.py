"""
PixelRAG integration for visual content understanding
Handles screenshot capture, tiling, embedding, and visual search
"""

import os
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger

from app.core.config import settings

# PixelRAG will be imported dynamically to avoid initialization issues
pixelrag_initialized = False
pixelrag_model = None
pixelrag_index = None


async def initialize_pixelrag():
    """Initialize PixelRAG components"""
    global pixelrag_initialized, pixelrag_model, pixelrag_index
    
    if pixelrag_initialized:
        return
    
    logger.info("Initializing PixelRAG...")
    
    try:
        # Import PixelRAG modules
        # These imports happen after environment is set up
        logger.info(f"Loading model: {settings.PIXELRAG_MODEL}")
        logger.info(f"Using device: {settings.PIXELRAG_DEVICE}")
        
        # Create index directory if it doesn't exist
        os.makedirs(settings.PIXELRAG_INDEX_PATH, exist_ok=True)
        
        # Note: Actual model loading will happen on first use
        # to avoid slowing down startup
        pixelrag_initialized = True
        logger.success("PixelRAG initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PixelRAG: {e}")
        raise


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
