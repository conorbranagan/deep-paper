from typing import Literal, Union, Optional
from enum import Enum
from pydantic import BaseModel


class ResearchStatus(str, Enum):
    STARTING = "starting"
    BROWSING = "browsing"
    ANALYZING = "analyzing"
    DONE = "done"


class ResearchStatusMessage(BaseModel):
    type: Literal["status"]
    status: ResearchStatus
    message: str


class ResearchSourceMessage(BaseModel):
    type: Literal["source"]
    url: str
    title: str
    favicon: str
    summary: Optional[str] = None


class ResearchContentMessage(BaseModel):
    type: Literal["content"]
    content: str


class ResearchError(BaseModel):
    type: Literal["error"]
    error: str


ResearchMessage = Union[
    ResearchStatusMessage, ResearchSourceMessage, ResearchContentMessage, ResearchError
]
