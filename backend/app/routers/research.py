from dotenv import load_dotenv
import datetime
import json

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.agents import researcher, summarizer
from app.agents.utils import step_as_json, is_agent_step
from app.models.paper import Paper, InvalidPaperURL, PaperNotFound
from app.config import settings


load_dotenv()

router = APIRouter()


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
        for chunk in generator_func:
            if await request.is_disconnected():
                break

            # Handle different types of chunks
            if is_agent_step(chunk):
                # Handle agent steps
                as_json = step_as_json(chunk)
                # Skip empty content actions
                if not as_json or not as_json.get("content"):
                    continue
                yield {
                    "event": "message",
                    "data": json.dumps(as_json),
                    "id": str(datetime.datetime.now().timestamp()),
                }
            elif hasattr(chunk, "choices") and hasattr(chunk.choices[0], "delta"):
                # Handle streaming LLM response
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {"type": "content", "content": chunk.choices[0].delta.content}
                    ),
                    "id": str(datetime.datetime.now().timestamp()),
                }
            else:
                raise Exception(f"Unknown chunk format: {chunk}")

    return EventSourceResponse(event_generator())


@router.get("/api/research/paper/query")
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


@router.get("/api/research/paper/summarize")
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


@router.get("/api/research/paper/topic")
async def summarize_topic(request: Request):
    url = request.query_params.get("url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide url",
        )
    topic = request.query_params.get("topic")
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide topic",
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

    return await create_event_source_response(
        request, summarizer.summarize_topic(paper, topic, model=model)
    )


@router.get("/api/research/explore")
async def explore(request: Request):
    query = request.query_params.get("query")
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide query",
        )
    model = request.query_params.get("model") or settings.DEFAULT_MODEL

    agent_model = settings.agent_model(
        model,
        0.2,
    )

    research_gen = researcher.run_research_agent(query, agent_model, stream=True)
    return await create_event_source_response(request, research_gen)
