from app.models.paper import Paper, PaperNotFound

from smolagents import Tool, CodeAgent
from smolagents.monitoring import LogLevel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever

from app.pipeline.vector_store import VectorStore, QdrantVectorStore, QdrantVectorConfig
from app.agents.observability import SmolLLMObs, wrap_llmobs
from app.config import settings
wrap_llmobs()

@SmolLLMObs.wrapped_tool
class PaperRetriever(Tool):
    name = "paper_retriever"
    description = (
        "Fetch a paper by the arxiv id and return the contents in LaTeX format"
    )
    inputs = {
        "arxiv_id": {
            "type": "string",
            "description": "ID of the arxiv paper, example is '2307.09288'",
        },
        "query": {
            "type": "string",
            "description": "Query to ask the paper. Leave this empty if you want the full paper.",
        },
    }
    output_type = "string"

    def forward(self, arxiv_id: str, query: str) -> str:
        try:
            paper = Paper.from_arxvid_id(arxiv_id)
        except PaperNotFound:
            return f"Unable to find paper for Arxiv ID {arxiv_id}"

        if query == "":
            return f"\nPaper Contents in LaTeX\n\n{paper.latex_contents()}"

        source_docs = [Document(c.as_text) for c in paper.latex_contents]
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            add_start_index=True,
            strip_whitespace=True,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        docs = text_splitter.split_documents(source_docs)
        retriever = BM25Retriever.from_documents(docs, k=10)

        retriever.invoke(query)
        return "\nRetrieved information:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n{doc.page_content}"
                for i, doc in enumerate(docs)
            ]
        )


@SmolLLMObs.wrapped_tool
class PaperChunkRetriever(Tool):
    name = "paper_chunk_retriever"
    description = "Query across our database of papers for chunk of text that matches a natural language query"
    inputs = {
        "query": {
            "type": "string",
            "description": "natural language query to search for",
        },
    }
    output_type = "string"

    def __init__(self, vector_store: VectorStore):
        super().__init__()
        self.vector_store = vector_store

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your search query must be a string"

        results = self.vector_store.search(query, top_k=10)
        return "\nRetrieved documents:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n{doc["metadata"]}\n\n{doc["document"]}"
                for i, doc in enumerate(results)
            ]
        )


@SmolLLMObs.wrapped_tool
class CitationRetriever(Tool):
    name = "citation_retriever"
    description = "Retrieve citations for a given paper"
    inputs = {
        "arxiv_id": {
            "type": "string",
            "required": True,
            "description": "ID of the arxiv paper, example is '2307.09288'",
        },
        "citation_ids": {
            "type": "array",
            "required": True,
            "description": "ID of the citation, these will appear as \\cite{<citation_id>} in the content. Just provide the <citation_id> values as an array.",
        },
    }
    output_type = "string"

    def forward(self, arxiv_id: str, citation_ids: list[str]) -> str:
        if arxiv_id == "" or len(citation_ids) == 0:
            return "Must provide both arxiv and citation ids"
        try:
            paper = Paper.from_arxvid_id(arxiv_id)
        except PaperNotFound:
            return f"Unable to find paper for Arxiv ID {arxiv_id}"

        matching = [c for c in paper.latex.citations if c.id in citation_ids]
        if len(matching) == 0:
            return f"Unable to find citations for Arxiv ID {arxiv_id} and IDs {citation_ids}"

        resp = ""
        for match in matching:
            resp += f"\n==== Citation Details ====\nID: {match.id}\nTitle: {match.title}\nAuthor: {match.author}\nYear: {match.year}\nURL: {match.url or "None"}"
        return resp


PAPER_PROMPT_TPL = """
You are researching the paper:

- Arxiv ID: {paper.arxiv_id}
- Title: {paper.latex.title}
- Abstract: {paper.latex.abstract}

When you are asked to reference other papers cited, you should be sure to fetch or query those papers as well to ensure you have the full context.

Please use your available to tools to answer the following prompt.

{prompt}
"""

def run_paper_agent(url, prompt, model, stream=False, verbosity_level=LogLevel.OFF):
    paper = Paper.from_url(url)
    agent = CodeAgent(
        tools=[
            PaperRetriever(),
            CitationRetriever(),
        ],
        model=model,
        max_steps=3,
        verbosity_level=verbosity_level,
    )

    system_prompt = PAPER_PROMPT_TPL.format(
        paper=paper,
        prompt=prompt,
    )

    return agent.run(system_prompt, stream=stream)


RESEARCH_PROMPT_TPL = """
You are supporting a researcher who is using a database of academic papers to answer questions.

Please use your available to tools to answer the following prompt.

{prompt}
"""


def run_research_agent(prompt, model, stream=False, verbosity_level=LogLevel.OFF):
    vector_store = QdrantVectorStore(
        url=settings.QDRANT_URL,
        config=QdrantVectorConfig.bert_384("papers"),
    )
    agent = CodeAgent(
        tools=[
            PaperChunkRetriever(vector_store),
        ],
        model=model,
        max_steps=3,
        verbosity_level=verbosity_level,
    )

    system_prompt = RESEARCH_PROMPT_TPL.format(
        prompt=prompt,
    )

    return agent.run(system_prompt, stream=stream)
