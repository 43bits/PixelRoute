"""
Visual query and search endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.core.database import prisma, get_db
from app.services.pixelrag import pixelrag_service

router = APIRouter()


class VisualQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language query about visual content")
    scraperId: Optional[str] = Field(None, description="Filter by scraper ID")
    nResults: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class VisualQueryResponse(BaseModel):
    queryId: str
    question: str
    results: List[dict]
    resultCount: int
    answer: Optional[str] = None
    duration: int  # milliseconds


@router.post("/visual")
async def query_visual_content(
    request: VisualQueryRequest,
    db = Depends(get_db)
) -> VisualQueryResponse:
    """
    Query visual content using natural language
    
    Example queries:
    - "Show me all price comparison tables"
    - "What are the trends in the charts?"
    - "Find products with red badges"
    """
    
    start_time = datetime.utcnow()
    
    try:
        # Perform visual search with PixelRAG
        search_results = await pixelrag_service.search_visual(
            query=request.question,
            scraper_id=request.scraperId,
            n_results=request.nResults
        )
        
        # Enrich results with database metadata
        enriched_results = []
        for result in search_results:
            # Try to find matching result in database
            embedding_id = result.get("id", "")
            
            # Look up in database
            db_result = None
            if embedding_id:
                db_results = await prisma.scraperresult.find_many(
                    where={"embeddingId": {"contains": embedding_id}},
                    take=1
                )
                if db_results:
                    db_result = db_results[0]
            
            enriched_result = {
                "score": result.get("score", 0),
                "snippet": result.get("snippet", ""),
                "imageUrl": result.get("image_url", ""),
                "metadata": {}
            }
            
            if db_result:
                enriched_result["metadata"] = {
                    "resultId": db_result.id,
                    "url": db_result.url,
                    "scrapedAt": db_result.scrapedAt.isoformat(),
                    "data": db_result.data
                }
            
            enriched_results.append(enriched_result)
        
        # Generate answer summary (basic implementation)
        answer = None
        if enriched_results:
            answer = f"Found {len(enriched_results)} visual results matching your query."
        
        # Store query in database
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        visual_query = await prisma.visualquery.create({
            "question": request.question,
            "scraperId": request.scraperId,
            "results": enriched_results,
            "resultCount": len(enriched_results),
            "answer": answer,
            "duration": duration_ms
        })
        
        return VisualQueryResponse(
            queryId=visual_query.id,
            question=request.question,
            results=enriched_results,
            resultCount=len(enriched_results),
            answer=answer,
            duration=duration_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual query failed: {str(e)}")


@router.get("/history")
async def get_query_history(
    skip: int = 0,
    limit: int = 20,
    scraper_id: Optional[str] = None,
    db = Depends(get_db)
):
    """Get query history"""
    
    where = {}
    if scraper_id:
        where["scraperId"] = scraper_id
    
    queries = await prisma.visualquery.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"}
    )
    
    total = await prisma.visualquery.count(where=where)
    
    return {
        "queries": queries,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{query_id}")
async def get_query(query_id: str, db = Depends(get_db)):
    """Get query details"""
    
    query = await prisma.visualquery.find_unique(where={"id": query_id})
    
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    return query


@router.post("/text")
async def query_text_content(
    question: str,
    scraper_id: Optional[str] = None,
    limit: int = 10,
    db = Depends(get_db)
):
    """
    Query scraped text content (non-visual search)
    Simple keyword-based search in scraped data
    """
    
    # Build search query
    where: dict = {}
    if scraper_id:
        where["scraperId"] = scraper_id
    
    # Search in JSON data field (basic implementation)
    # In production, use full-text search or Elasticsearch
    results = await prisma.scraperresult.find_many(
        where=where,
        take=limit,
        order={"scrapedAt": "desc"}
    )
    
    # Filter results that might match the query
    # This is a simple implementation - enhance with proper text search
    filtered_results = []
    question_lower = question.lower()
    
    for result in results:
        # Convert data to string and search
        data_str = str(result.data).lower()
        if question_lower in data_str or any(word in data_str for word in question_lower.split()):
            filtered_results.append({
                "id": result.id,
                "url": result.url,
                "data": result.data,
                "scrapedAt": result.scrapedAt.isoformat()
            })
    
    return {
        "question": question,
        "results": filtered_results,
        "count": len(filtered_results)
    }
