
from app.models.paper import Paper, PaperNotFound

from smolagents import Tool, CodeAgent
from smolagents.monitoring import LogLevel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever
from langsmith import traceable


class PaperRetriever(Tool):
    name = "paper_retriever"
    description = "Fetch a paper by the arxiv id and return the contents in LaTeX format"
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

        source_docs = [Document(c.as_text) for c in paper.contents]
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
                f"\n\n===== Document {str(i)} =====\n" + doc.page_content
                for i, doc in enumerate(docs)
            ]
        )


class CitationRetriever(Tool):
    name = "citation_retriever"
    description = "Retrieve details of a citation by arxiv id and one or more citation ids. You must have both! Returns the title, author and url"
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

        matching = [c for c in paper.citations if c.id in citation_ids]
        if len(matching) == 0:
            return f"Unable to find citations for Arxiv ID {arxiv_id} and IDs {citation_ids}"

        resp = ""
        for match in matching:
            resp += f"\n==== Citation Details ====\nID: {match.id}\nTitle: {match.title}\nAuthor: {match.author}\nYear: {match.year}\nURL: {match.url or "None"}"
        return resp


prompt_tpl = """
You are researching the paper:

- Arxiv ID: {paper.arxiv_id}
- Title: {paper.latex.title}
- Abstract: {paper.latex.abstract}

When you are asked to reference other papers cited, you should be sure to fetch or query those papers as well to ensure you have the full context.

Please use your available to tools to answer the following prompt.

{prompt}
"""


@traceable
def run(url, prompt, model, stream=False, verbosity_level=LogLevel.OFF):
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

    system_prompt = prompt_tpl.format(
        paper=paper,
        prompt=prompt,
    )

    return agent.run(system_prompt, stream=stream)
