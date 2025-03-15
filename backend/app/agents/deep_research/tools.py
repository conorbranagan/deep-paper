from typing import Optional
import queue
import threading
import os
import re
import json
import logging

from smolagents import Tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
import requests

from app.pipeline.embedding import EmbeddingConfig
from app.pipeline.chunk import MaxLengthChunkingStrategy
from app.pipeline.vector_store import VectorStore
from app.models.paper import Paper, PaperNotFound
from app.agents.dd_llmobs import SmolLLMObs
from app.agents.deep_research.message import (
    ResearchStatusMessage,
    ResearchSourceMessage,
)

log = logging.getLogger(__name__)


class ResearchTool(Tool):
    def __init__(
        self,
        message_queue: queue.Queue,
        queue_lock: threading.Lock,
    ):
        super().__init__()
        self.message_queue = message_queue
        self.queue_lock = queue_lock

    def forward(self, *args, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement this method")


@SmolLLMObs.wrapped_tool
class PaperRetriever(ResearchTool):
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
            paper = Paper.from_arxiv_id(arxiv_id)
        except PaperNotFound:
            return f"Unable to find paper for Arxiv ID {arxiv_id}"

        if self.message_queue and self.queue_lock:
            with self.queue_lock:
                self.message_queue.put(
                    ResearchStatusMessage(
                        type="status",
                        message=f'Analyzing "{paper.latex.title}" (arXiv:{arxiv_id})...',
                    )
                )

        log.info(f"Analyzing paper {arxiv_id} with query {query}")
        if query is None or not query.strip():
            return f"\nPaper Contents\n\n{paper.contents()}"

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            add_start_index=True,
            strip_whitespace=True,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        chunks = text_splitter.split_text(paper.contents())
        retriever = BM25Retriever.from_texts(chunks, k=10)

        retriever.invoke(query)
        return "\nRetrieved information:\n" + "".join(
            [
                f"\n\n===== Chunk {str(i)} =====\n{chunk}"
                for i, chunk in enumerate(chunks)
            ]
        )


@SmolLLMObs.wrapped_tool
class VisitWebpageTool(ResearchTool):
    name = "visit_webpage"  # Keeping named so Agent is not aware this is different from just visiting the page.
    description = "Visits a webpage at the given url and reads its content as a markdown string. Use this to browse webpages."
    inputs = {
        "url": {
            "type": "string",
            "description": "The url of the webpage to visit.",
        }
    }
    output_type = "string"

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_config: EmbeddingConfig,
        message_queue: queue.Queue,
        queue_lock: threading.Lock,
    ):
        super().__init__(message_queue, queue_lock)
        self.vector_store = vector_store
        self.embedding_config = embedding_config
        self.visited_urls: dict[str, str] = {}

    def _get_webpage_content(self, url: str) -> tuple[str, str]:
        try:
            import requests
            from markdownify import markdownify
            from bs4 import BeautifulSoup
            from smolagents.utils import truncate_content
        except ImportError as e:
            raise ImportError(
                "You must install packages `markdownify`, `requests`, and `bs4` to run this tool: for instance run `pip install markdownify requests beautifulsoup4`."
            ) from e

        # Send a GET request to the URL with a 20-second timeout
        response = requests.get(url, timeout=20)
        response.raise_for_status()  # Raise an exception for bad status codes
        html_content = response.text

        # Parse the HTML to extract title and favicon
        soup = BeautifulSoup(html_content, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string
        else:
            title = "Unknown Title"

        # Convert the HTML content to Markdown
        markdown_content = markdownify(html_content).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return str(truncate_content(markdown_content, 10000)), title

    def forward(self, url: str) -> str:
        log.info(f"Visiting webpage {url}")
        if url in self.visited_urls:
            return self.visited_urls[url]

        try:
            content, title = self._get_webpage_content(url)
            summary = content[:200] + "..." if len(content) > 200 else content

            with self.queue_lock:
                self.message_queue.put(
                    ResearchSourceMessage(
                        type="source",
                        url=url,
                        title=title,
                        favicon=f"http://www.google.com/s2/favicons?domain={url}",
                        summary=summary,
                    )
                )

            metadata = {"url": url, "title": title}
            content_with_metadata = f"URL: {url}\nTitle: {title}\nContent: {content}"
            documents = MaxLengthChunkingStrategy(
                max_tokens=self.embedding_config.max_tokens
            ).chunk(content_with_metadata)
            self.vector_store.add_documents(documents, [metadata] * len(documents))

            self.visited_urls[url] = content_with_metadata
            return content_with_metadata

        except Exception as e:
            error_message = f"Error fetching the webpage {url}: {str(e)}"
            return error_message


@SmolLLMObs.wrapped_tool
class QueryFindingsTool(Tool):
    name = "QueryFindingsTool"
    description = "A tool that queries the vector store for information to help with the research report."
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to search the vector store for",
        },
    }
    output_type = "string"

    def __init__(self, vector_store: VectorStore, embedding_config: EmbeddingConfig):
        super().__init__()
        self.vector_store = vector_store
        self.embedding_config = embedding_config

    def forward(self, query: str) -> str:
        log.info(f"Querying findings for {query}")
        results = self.vector_store.search(query, top_k=10)
        return "\nRetrieved documents from sources:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n{doc.metadata}\n\n{doc.document}"
                for i, doc in enumerate(results)
            ]
        )


@SmolLLMObs.wrapped_tool
class GoogleSearchTool(ResearchTool):
    name = "web_search"
    description = """Performs a google web search for your query then returns a string of the top search results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
        "date_lookback": {
            "type": "string",
            # TODO: does serper support date range?
            "description": "Optionally restrict results to a certain date lookback. Choose from: h, d, w, m, y.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(
        self,
        message_queue: queue.Queue,
        queue_lock: threading.Lock,
    ):
        super().__init__(message_queue, queue_lock)
        self.serper_api_key = os.getenv("SERPER_API_KEY")

    def forward(
        self,
        query: str,
        date_lookback: Optional[str] = None,
    ) -> str:
        log.info(f"Searching the web for {query} with date lookback {date_lookback}")
        with self.queue_lock:
            self.message_queue.put(
                ResearchStatusMessage(
                    type="status",
                    message="Searching the web...",
                )
            )

        if self.serper_api_key is None:
            raise ValueError(
                "Missing Serper API key. Make sure you have 'SERPER_API_KEY' in your env variables."
            )

        data = {"q": query}
        if date_lookback is not None:
            data["tbs"] = f"qdr:{date_lookback}"
        headers = {"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"}
        response = requests.post(
            "https://google.serper.dev/search", headers=headers, data=json.dumps(data)
        )

        if response.status_code == 200:
            json_response = response.json()
        else:
            raise ValueError(response.json())

        if "organic" not in json_response.keys():
            raise Exception(f"No results found for query: '{query}'")

        if "organic" not in json_response.keys():
            raise Exception(
                f"No results found for query: '{query}'. Use a less restrictive query."
            )
        if len(json_response["organic"]) == 0:
            raise Exception(f"No results found for query: '{query}'")

        results = []
        for page in json_response["organic"]:
            date_published = ""
            if "date" in page:
                date_published = "\nDate published: " + page["date"]

            snippet = ""
            if "snippet" in page:
                snippet = "\n" + page["snippet"]

            redacted_version = f"{page['position']}. [{page['title']}]({page['link']}){date_published}\n{snippet}"
            results.append(redacted_version)

        return "## Search Results\n" + "\n\n".join(results)
