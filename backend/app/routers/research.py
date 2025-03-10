from dotenv import load_dotenv
import json
import asyncio
import logging


from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.agents import researcher, summarizer, explore
from app.agents.utils import step_as_json, is_agent_step
from app.models.paper import Paper, InvalidPaperURL, PaperNotFound
from app.config import settings


log = logging.getLogger(__name__)

load_dotenv()

router = APIRouter(prefix="/api/research")


async def create_event_source_response(request: Request, generator_func):
    """
    Creates an EventSourceResponse from a generator function.

    Args:
        request: The FastAPI request object
        generator_func: A function that yields data to be sent as events

    Returns:
        EventSourceResponse: The SSE response
    """

    async def event_generator():
        try:
            for chunk in generator_func:
                if await request.is_disconnected():
                    break

                # Handle different types of chunks
                if is_agent_step(chunk):
                    as_json = step_as_json(chunk)
                    # Skip empty content actions
                    if not as_json or not as_json.get("content"):
                        continue
                    yield dict(data=json.dumps(as_json))
                elif hasattr(chunk, "choices") and hasattr(chunk.choices[0], "delta"):
                    yield dict(
                        data=json.dumps(
                            {"type": "content", "content": chunk.choices[0].delta.content}
                        )
                    )
                else:
                    yield dict(data=json.dumps(chunk))
        except asyncio.CancelledError as e:
            log.info("Disconnected from client (via refresh/close)")
            # Do any other cleanup, if any
            raise e

    return EventSourceResponse(event_generator())


@router.get("/paper/query")
async def stream(request: Request):
    paper_url = request.query_params.get("paper_url")
    query = request.query_params.get("query")
    model = request.query_params.get("model") or settings.DEFAULT_MODEL
    if not paper_url or not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide paper_url and query",
        )

    agent_model = settings.agent_model(
        model,
        0.2,
    )
    researcher_gen = researcher.run_paper_agent(
        paper_url, query, agent_model, stream=True
    )

    return await create_event_source_response(request, researcher_gen)


@router.get("/paper/summarize")
async def summarize(request: Request):
    url = request.query_params.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide url",
        )
    model = request.query_params.get("model") or settings.DEFAULT_MODEL
    try:
        paper = Paper.from_url(url)
    except InvalidPaperURL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="url is not a valid arxiv url",
        )
    except PaperNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no research found for id={id}",
        )

    return summarizer.summarize_paper(paper, model=model)


@router.get("/paper/topic")
async def summarize_topic(request: Request):
    url = request.query_params.get("url")
    topic = request.query_params.get("topic")
    model = request.query_params.get("model") or settings.DEFAULT_MODEL
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide url",
        )
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide topic",
        )

    try:
        paper = Paper.from_url(url)
    except InvalidPaperURL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="url is not a valid arxiv url",
        )
    except PaperNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no research found for id={id}",
        )
    stream = summarizer.summarize_topic(paper, topic, model=model)
    return await create_event_source_response(request, stream)


@router.get("/explore")
async def explore_query(request: Request):
    query = request.query_params.get("query")
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide query",
        )
    model = request.query_params.get("model") or settings.DEFAULT_MODEL

    return explore.explore_query(query, model=model)
