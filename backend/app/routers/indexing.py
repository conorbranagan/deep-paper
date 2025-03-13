from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import modal


log = logging.getLogger(__name__)

router = APIRouter(prefix="/indexing")


class IndexPaperRequest(BaseModel):
    url: str


class IndexPaperBatchRequest(BaseModel):
    urls: List[str]


class IndexPaperResponse(BaseModel):
    object_id: str
    url: str
    status: str


class IndexPaperBatchResponse(BaseModel):
    object_id: str
    urls: List[str]
    status: str


class TaskStatusResponse(BaseModel):
    object_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[float] = None


@router.post("/paper", response_model=IndexPaperResponse)
async def submit_paper_for_indexing(request: IndexPaperRequest):
    """Submit a paper for indexing"""
    try:
        index_job = modal.Function.from_name("paper_indexer", "index_single")
        call = index_job.spawn(request.url)

        return IndexPaperResponse(
            object_id=call.object_id, url=request.url, status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{object_id}", response_model=TaskStatusResponse)
async def get_task_status(object_id: str):
    """Get the status of an indexing task"""
    function_call = modal.FunctionCall.from_id(object_id)
    try:
        result = function_call.get(timeout=5)
    except modal.exception.OutputExpiredError:
        result = {"result": "expired"}
    except TimeoutError:
        result = {"result": "pending"}
    return result


@router.post("/papers/batch", response_model=IndexPaperBatchResponse)
async def submit_papers_batch_for_indexing(request: IndexPaperBatchRequest):
    """Submit multiple papers for indexing"""
    try:
        index_job = modal.Function.from_name("paper_indexer", "index_batch")
        call = index_job.spawn(request.urls)

        return IndexPaperBatchResponse(
            object_id=call.object_id, urls=request.urls, status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
