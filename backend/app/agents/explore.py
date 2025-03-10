from pydantic import BaseModel
import litellm

from app.models.paper import Paper
from app.config import settings
from app.pipeline.vector_store import QdrantVectorStore
from app.pipeline.embedding import Embedding

EXPLORE_PROMPT = """
You are exploring the topic or question: {explore_topic}

You are using the following source documents to answer the question or provide an overview of the topic.

BEGIN SOURCE DOCUMENT

{paper_chunks}

END SOURCE DOCUMENTS 

- Please describe the topic or answer the question ONLY using the data in source documents.
- Provide a response in no more than 2 paragraphs.
- You must inline source cituations by Arxiv ID. 
- Citations should only appear once in the list of citations.
- Citations should be in the format of "For instance, BARTScore (2206.05802) estimates factuality by looking at the conditional probability" where "2206.05802" is a paper ID for a citation.
"""

# FIXME: Do we need to use the same citations as provided in the raw lat


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
    title: str
    arxiv_id: str
    chunk: str


def run_explore(
    explore_topic: str,
    model: str = settings.DEFAULT_MODEL,
    top_k=5,
) -> ExploreResponse:
    vector_store = QdrantVectorStore(
        url=settings.QDRANT_URL,
        collection_name="papers",
        embedding_config=Embedding.default(),
    )
    results = vector_store.search(explore_topic, top_k)
    chunks = [
        PaperChunk(
            title=r.metadata["paper_title"],
            arxiv_id=r.metadata["paper_id"],
            chunk=r.document,
        )
        for r in results
    ]
    paper_chunks = "\n".join(
        [f"Title: {c.title}\nArxiv ID: {c.arxiv_id}\nChunk: {c.chunk}" for c in chunks]
    )

    formatted_prompt = EXPLORE_PROMPT.format(
        explore_topic=explore_topic,
        paper_chunks=paper_chunks,
    )
    print(formatted_prompt)
    llm_response = (
        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0.3,
            response_format=ExplorePromptResponse,
        )
        .choices[0]
        .message.content
    )

    raw_response = ExplorePromptResponse.model_validate_json(llm_response)

    citations = {}
    for citation_id in raw_response.citation_ids:
        if citation_id not in citations:
            paper = Paper.from_arxiv_id(citation_id)
            citations[citation_id] = Citation(
                title=paper.latex.title,
                arxiv_id=citation_id,
            )
    return ExploreResponse(response=raw_response.response, citations=citations)
