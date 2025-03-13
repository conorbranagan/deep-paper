from typing import Generator
from pydantic import BaseModel
import litellm
import re
import uuid
import logging

from app.config import settings
from app.pipeline.vector_store import QdrantVectorStore
from app.pipeline.embedding import Embedding

log = logging.getLogger(__name__)

citation_id_regex = re.compile(
    r"citation_id:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)

EXPLORE_PROMPT = """
You are exploring the topic or question: {explore_topic}

You are using the following source documents to answer the question or provide an overview of the topic.
Each document will have a UUID associated with it that you can reference in your response.

BEGIN SOURCE DOCUMENT

{paper_chunks}

END SOURCE DOCUMENTS 

- Please describe the topic or answer the question ONLY using the data in source documents.
- You must inline source cituations by Citation ID with the format "(citation_id:<citation_id>)"

Formatting:
    - Use the markdown format for the response.
    - Make it like a report with a headling, potentially some section headers and the content.
    - There should be no more than 4 paragraphs total.

Here are some examples of valid citations:

    collaborative frameworks involving multiple language models (citation_id:9cbc613d-e047-4c16-9d41-be95014e4f12)
    the BARTScore metric (citation_id:123e4567-e89b-12d3-a456-426614174000)
    as described in Google's T5 paper (citation_id:123e4567-e89b-12d3-a456-426614174000)
    
"""


class Citation(BaseModel):
    title: str
    arxiv_id: str


class ExplorePromptResponse(BaseModel):
    response: str
    citation_ids: list[str]


class ExploreResponse(BaseModel):
    response: str
    citations: dict[str, Citation]


class PaperChunk(BaseModel):
    id: str
    title: str
    arxiv_id: str
    chunk: str
    section: str
    subsection: str


def explore_query(
    explore_topic: str,
    model: str = settings.DEFAULT_MODEL,
    top_k=5,
) -> Generator[str | PaperChunk, None, None]:
    vector_store = QdrantVectorStore.instance(
        collection_name=QdrantVectorStore.PAPERS_COLLECTION,
        embedding_config=Embedding.default(),
    )
    results = vector_store.search(explore_topic, top_k)
    chunks = [
        PaperChunk(
            id=str(uuid.uuid4()),
            title=r.metadata["paper_title"],
            arxiv_id=r.metadata["paper_id"],
            section=r.metadata.get("section", ""),
            subsection=r.metadata.get("subsection", ""),
            chunk=r.document,
        )
        for r in results
    ]
    chunks_by_id = {c.id: c for c in chunks}
    paper_chunks = "\n".join(
        [
            f"Chunk ID: {c.id}\nTitle: {c.title}\nArxiv ID: {c.arxiv_id}\nChunk: {c.chunk}"
            for c in chunks
        ]
    )

    formatted_prompt = EXPLORE_PROMPT.format(
        explore_topic=explore_topic,
        paper_chunks=paper_chunks,
    )
    print(formatted_prompt)
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": formatted_prompt}],
        temperature=0.3,
        stream=True,
        vertex_credentials=settings.VERTEX_CREDENTIALS_JSON,
    )

    buffer = ""
    seen_ids = set()

    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            buffer += content
            citation_ids = citation_id_regex.findall(buffer)
            for citation_id in citation_ids:
                if citation_id not in seen_ids:
                    seen_ids.add(citation_id)
                    chunk = chunks_by_id.get(citation_id)
                    if chunk:
                        yield chunk
                    else:
                        log.warning("Chunk {citation_id} not found in chunks")

            yield content
