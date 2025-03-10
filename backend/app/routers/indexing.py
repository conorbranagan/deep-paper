from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from celery.result import AsyncResult

from app.tasks.indexing import index_paper, index_papers_batch

router = APIRouter(prefix="/indexing")

class IndexPaperRequest(BaseModel):
    arxiv_id: str

class IndexPaperBatchRequest(BaseModel):
    arxiv_ids: List[str]

class IndexPaperResponse(BaseModel):
    task_id: str
    arxiv_id: str
    status: str

class IndexPaperBatchResponse(BaseModel):
    task_id: str
    arxiv_ids: List[str]
    status: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[float] = None

@router.post("/papers", response_model=IndexPaperResponse)
async def submit_paper_for_indexing(request: IndexPaperRequest):
    """Submit a paper for indexing"""
    try:
        # Queue the indexing task
        task = index_paper.delay(request.arxiv_id)
        
        return IndexPaperResponse(
            task_id=task.id,
            arxiv_id=request.arxiv_id,
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/papers/batch", response_model=IndexPaperBatchResponse)
async def submit_papers_batch_for_indexing(request: IndexPaperBatchRequest):
    """Submit multiple papers for indexing"""
    try:
        # Queue the batch indexing task
        task = index_papers_batch.delay(request.arxiv_ids)
        
        return IndexPaperBatchResponse(
            task_id=task.id,
            arxiv_ids=request.arxiv_ids,
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of an indexing task"""
    task_result = AsyncResult(task_id)
    
    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.status,
    )
    
    # Add result or error information if available
    if task_result.successful():
        response.result = task_result.result
        if isinstance(response.result, dict) and "progress" in response.result:
            response.progress = response.result["progress"]
    elif task_result.failed():
        response.error = str(task_result.result)
    elif task_result.state == 'PROGRESS' and task_result.info:
        response.progress = task_result.info.get('progress', 0)
    
    return response 