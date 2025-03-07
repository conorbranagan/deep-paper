from dotenv import load_dotenv
import datetime
import json
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.agents import researcher
from app.agents.utils import step_as_json
from app.models.paper import Paper, InvalidPaperURL, PaperNotFound
from backend.app.agents.summarizer import summarize_paper, run
from app.config import settings


load_dotenv()

router = APIRouter()


@router.get("/api/research/deep")
async def stream(request: Request):
    url = request.query_params.get("url")
    question = request.query_params.get("question")
    model = request.query_params.get("model") or settings.DEFAULT_MODEL
    if not url or not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide url and question",
        )


    agent_model = settings.agent_model(model, 0.2, metadata={
        "metadata": {
            "run_name": "paper-research",
            "project_name": "deep-paper",
            "trace_id": uuid.uuid4().hex,
        },
    })
    researcher_gen = researcher.run(url, question, agent_model, stream=True)

    async def event_generator():
        for agent_step in researcher_gen:
            if await request.is_disconnected():
                break

            as_json = step_as_json(agent_step)
            # HACK: we get empty content actions for some reason? need to look into it.
            if not as_json or not as_json.get("content"):
                continue
            yield {
                "event": "message",
                "data": json.dumps(as_json),
                "id": str(datetime.datetime.now().timestamp()),
            }

    return EventSourceResponse(event_generator())


@router.get("/api/research/summarize")
async def summarize(request: Request):
    url = request.query_params.get("url")
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

    return summarize_paper(paper, model=model)


@router.get("/api/research/summarize/topic")
async def summarize_topic(request: Request):
    url = request.query_params.get("url")
    topic = request.query_params.get("topic")
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

    async def event_generator():
        for chunk in run(paper, topic, model=model):
            if await request.is_disconnected():
                break
            yield {
                "event": "message",
                "data": json.dumps(
                    {"type": "content", "content": chunk.choices[0].delta.content}
                ),
                "id": str(datetime.datetime.now().timestamp()),
            }

    return EventSourceResponse(event_generator())
