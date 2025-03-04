from typing import Any, Optional
from dotenv import load_dotenv
import datetime
import uuid
import os
import json

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from smolagents import LiteLLMModel

from app.agents import researcher
from app.agents.utils import step_as_json
from app.models.research import RESEARCH_DB, Research
from app.models.paper import Paper, InvalidPaperURL, PaperNotFound
from app.prompts import summarize_paper


load_dotenv()

router = APIRouter()


class StartResearchRequest(BaseModel):
    url: str


@router.post("/api/research/start")
async def start(request: StartResearchRequest):
    research_id = uuid.uuid4().hex
    RESEARCH_DB.set(research_id, Research(id=research_id, url=request.url))
    return {"researchId": research_id}


@router.get("/api/research/stream")
async def stream(request: Request):
    research_id = request.query_params.get("id")
    if not research_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Id needed to stream research",
        )

    research = RESEARCH_DB.get(research_id)
    if not research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no research found for id={id}",
        )

    model = LiteLLMModel(
        "openai/gpt-4o-mini",
        temperature=0.2,
        api_key=os.environ["OPENAI_API_KEY"],
    )
    researcher_gen = researcher.run(
        research.url, "Summarize this paper", model, stream=True
    )

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
async def start(request: Request):
    url = request.query_params.get("url")
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

    return summarize_paper(paper)
