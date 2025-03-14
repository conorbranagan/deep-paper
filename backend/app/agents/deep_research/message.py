from typing import Literal, Union, Optional
from pydantic import BaseModel


class ResearchStatusMessage(BaseModel):
    type: Literal["status"]
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
