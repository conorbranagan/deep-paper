from dotenv import load_dotenv
import json
import asyncio
import logging


from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse
from smolagents.monitoring import LogLevel

from app.agents import researcher, summarizer, explore, deep_research
from app.agents.utils import step_as_json, is_agent_step
from app.models.paper import Paper, InvalidPaperURL, PaperNotFound
from app.config import settings


log = logging.getLogger(__name__)

load_dotenv()

router = APIRouter(prefix="/api")


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
                            {
                                "type": "content",
                                "content": chunk.choices[0].delta.content,
                            }
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

    researcher_gen = researcher.run_paper_agent(paper_url, query, model, stream=True)

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
    stream = explore.explore_query(query, model=model)

    async def event_generator():
        try:
            for chunk in stream:
                if await request.is_disconnected():
                    break
                if isinstance(chunk, str):
                    yield dict(data=json.dumps({"type": "content", "content": chunk}))
                elif isinstance(chunk, explore.PaperChunk):
                    yield dict(
                        data=json.dumps(
                            {
                                "type": "citation",
                                "payload": {
                                    "id": chunk.id,
                                    "title": chunk.title,
                                    "arxiv_id": chunk.arxiv_id,
                                    "section": chunk.section,
                                    "subsection": chunk.subsection,
                                },
                            }
                        )
                    )
        except asyncio.CancelledError as e:
            log.info("Disconnected from client (via refresh/close)")
            # Do any other cleanup, if any
            raise e

    return EventSourceResponse(event_generator())


@router.get("/paper/deep-research")
async def paper_deep_research(request: Request):
    url = request.query_params.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide url",
        )
    model = request.query_params.get("model") or settings.DEFAULT_MODEL
    mode = request.query_params.get("mode")
    try:
        agent_mode = deep_research.AgentMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode, choose from: {', '.join(m.value for m in deep_research.AgentMode)}",
        )
    stream = deep_research.run_agent(
        agent_mode, url, model, verbosity_level=LogLevel.OFF
    )

    async def event_generator():
        try:
            for chunk in stream:
                if await request.is_disconnected():
                    break
                yield dict(data=chunk.model_dump_json())
        except asyncio.CancelledError as e:
            log.info("Disconnected from client (via refresh/close)")
            # Do any other cleanup, if any
            raise e

    return EventSourceResponse(event_generator())
