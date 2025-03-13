from datetime import datetime
from typing import Optional
import re
import requests
from app.models.paper import Paper, PaperNotFound

from smolagents import (
    Tool,
    CodeAgent,
    ToolCallingAgent,
)
from smolagents.monitoring import LogLevel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from app.pipeline.vector_store import VectorStore, QdrantVectorStore
from app.pipeline.embedding import Embedding, EmbeddingConfig
from app.pipeline.chunk import MaxLengthChunkingStrategy
from app.agents.dd_llmobs import SmolLLMObs, wrap_llmobs

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
            paper = Paper.from_arxiv_id(arxiv_id)
        except PaperNotFound:
            return f"Unable to find paper for Arxiv ID {arxiv_id}"

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
                f"\n\n===== Document {str(i)} =====\n{doc.metadata}\n\n{doc.document}"
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
            paper = Paper.from_arxiv_id(arxiv_id)
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
    vector_store = QdrantVectorStore.instance(
        collection_name=QdrantVectorStore.PAPERS_COLLECTION,
        embedding_config=Embedding.default(),
    )
    agent = CodeAgent(
        tools=[
            PaperChunkRetriever(vector_store),
            CitationRetriever(),
        ],
        model=model,
        max_steps=3,
        verbosity_level=verbosity_level,
    )

    system_prompt = RESEARCH_PROMPT_TPL.format(
        prompt=prompt,
    )

    return agent.run(system_prompt, stream=stream)


@SmolLLMObs.wrapped_tool
class FakeGoogleSearchTool(Tool):
    name = "GoogleSearchTool"  # Keeping named so Agent is not aware this is fake.
    description = (
        "A tool that searches the web for information to help with the research report."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to search the web for",
        },
    }
    output_type = "string"

    results_by_keywords = {
        (
            "mmlu",
            "2009.03300",
        ): """
0. |MMLU: Measuring Massive Multitask language Understanding ...](https://sh-tsang.medium.com/brief-review-mmlu-measuring-massive-multitask-language-understanding-7b18e7cbbeab)
Source: Medium · Sik-Ho Tsang

MMLU Dataset With 57 Tasks. “Brief Review — MMLU: Measuring Massive Multitask language Understanding” is published by Sik-Ho Tsang.

1. |What Is Multi-Task Language Understanding or MMLU?](https://cobusgreyling.medium.com/what-is-multi-task-language-understanding-or-mmlu-22e93e036c49)
Source: Medium

Measuring Massive Multitask Language Understanding. We propose a new test to measure a text model's multitask accuracy. The test covers 57 tasks including ...

2. |Massive Multitask Language Understanding (MMLU) in ...](https://medium.com/thedeephub/massive-multitask-language-understanding-mmlu-in-gpt-4-gemini-and-mistral-845e1dd4f77d)
Source: Medium

3.- |2009.03300] Measuring Massive Multitask Language Understanding (arxiv.org). 4.- Gemini — Google DeepMind. 5.- MMLU Dataset | Papers With Code. 6.- An ...

3. |Preliminary Analysis of MMLU-by-task - Corey Morris](https://coreymorrisdata.medium.com/preliminary-analysis-of-mmlu-evaluation-data-insights-from-500-open-source-models-e67885aa364b)
Source: Medium · Corey Morris

Recently Hugging face released a dataset of evaluation results for the Measuring Massive Multitask Language Understanding (MMLU) evaluation.

4. |Benchmark of LLMs (Part 2): MMLU, HELM, Eleuthera AI ...](https://medium.com/aimonks/benchmark-of-llms-part-2-mmlu-helm-eleuthera-ai-lm-eval-e6fc54053e3d)
Source: Medium · Michael X

|15] Hendrycks D, Burns C, Basart S, et al. Measuring massive multitask language understanding|J]. arXiv preprint arXiv:2009.03300, 2020. |16] Zellers R, ...

5. |Understanding Quality Metrics in Language Models: MMLU ...](https://medium.com/@jx.demesa/understanding-quality-metrics-in-language-models-mmlu-gpqa-math-and-more-3d80fba17906)
Source: Medium

Hendrycks, D., Burns, C., Basart, S., Zou, H., Song, C., & Dietterich, T. (2021). Measuring Massive Multitask Language Understanding. arXiv preprint arXiv: ...

6. |Evaluating Large Language Models](https://cset.georgetown.edu/article/evaluating-large-language-models/)
Date published: Jul 17, 2024
Source: CSET | Center for Security and Emerging Technology

Measuring Massive Multitask Language Understanding (MMLU) includes multiple-choice questions from professional exams on topics ranging from the law to ...

7. |How to Evaluate Multilingual LLMs in Any Language](https://medium.com/towards-data-science/how-to-evaluate-multilingual-llms-with-global-mmlu-ce314aedee8f)
Source: Medium

Hendrycks, Measuring Massive Multitask Language Understanding, GitHub repository from the user hendrycks. |5] Meta AI, Llama-3.2–1B-Instruct, Hugging Face ...

8. |Getting Started with Large Language Models: Pretraining |Part ...](https://medium.com/gopenai/getting-started-with-large-language-models-pretraining-part-1-3-783274bc42a9)
Source: medium.com

|2] Hendrycks, Dan, et al. Measuring Massive Multitask Language Understanding. arXiv:2009.03300, arXiv, 12 Jan. 2021. arXiv.org, http://arxiv.org/abs/2009.03300 ...

9. |Large Language Models: An Applied Econometric ...](https://bfi.uchicago.edu/wp-content/uploads/2025/01/BFI_WP_2025-10.pdf)
Date published: Jan 13, 2025
Source: Becker Friedman Institute
"""
    }

    def forward(self, query: str) -> str:
        for keywords, results in self.results_by_keywords.items():
            if any(keyword in query for keyword in keywords):
                return results
        return "No results found for query: " + query


@SmolLLMObs.wrapped_tool
class PersistingVisitWebpageTool(Tool):
    name = "visit_webpage"  # Keeping named so Agent is not aware this is different from just visiting the page.
    description = "Visits a webpage at the given url and reads its content as a markdown string. Use this to browse webpages."
    inputs = {
        "url": {
            "type": "string",
            "description": "The url of the webpage to visit.",
        }
    }
    output_type = "string"

    def __init__(self, vector_store: VectorStore, embedding_config: EmbeddingConfig):
        super().__init__()
        self.vector_store = vector_store
        self.embedding_config = embedding_config

    def _get_webpage_content(self, url: str) -> str:
        try:
            import requests
            from markdownify import markdownify

            from smolagents.utils import truncate_content
        except ImportError as e:
            raise ImportError(
                "You must install packages `markdownify` and `requests` to run this tool: for instance run `pip install markdownify requests`."
            ) from e

        # Send a GET request to the URL with a 20-second timeout
        response = requests.get(url, timeout=20)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return str(truncate_content(markdown_content, 10000))

    def forward(self, url: str) -> str:
        try:
            content = self._get_webpage_content(url)
        except requests.exceptions.Timeout:
            return "The request timed out. Please try again later or check the URL."
        except requests.exceptions.RequestException as e:
            return f"Error fetching the webpage: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

        metadata = {"url": url}
        content = f"URL: {url}\nContent: {content}"
        documents = MaxLengthChunkingStrategy(
            max_tokens=self.embedding_config.max_tokens
        ).chunk(content)
        self.vector_store.add_documents(documents, [metadata] * len(documents))

        return content


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
        results = self.vector_store.search(query, top_k=10)
        return "\nRetrieved documents from sources:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n{doc.metadata}\n\n{doc.document}"
                for i, doc in enumerate(results)
            ]
        )


@SmolLLMObs.wrapped_tool
class CustomGoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs a google web search for your query then returns a string of the top search results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
        "filter_year_min": {
            "type": "integer",
            "description": "Optionally restrict results to a certain year",
            "nullable": True,
        },
        "filter_year_max": {
            "type": "integer",
            "description": "Optionally restrict results to a certain year",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self):
        super().__init__(self)
        import os

        self.serpapi_key = os.getenv("SERPAPI_API_KEY")

    def forward(
        self,
        query: str,
        filter_year_min: Optional[int] = None,
        filter_year_max: Optional[int] = None,
    ) -> str:
        import requests

        if self.serpapi_key is None:
            raise ValueError(
                "Missing SerpAPI key. Make sure you have 'SERPAPI_API_KEY' in your env variables."
            )

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_key,
            "google_domain": "google.com",
        }
        if filter_year_min is not None and filter_year_max is not None:
            params["tbs"] = (
                f"cdr:1,cd_min:01/01/{filter_year_min},cd_max:12/31/{filter_year_max}"
            )
        elif filter_year_min is not None:
            params["tbs"] = f"cdr:1,cd_min:01/01/{filter_year_min}"
        elif filter_year_max is not None:
            params["tbs"] = f"cdr:1,cd_max:12/31/{filter_year_max}"

        response = requests.get("https://serpapi.com/search.json", params=params)

        if response.status_code == 200:
            results = response.json()
        else:
            raise ValueError(response.json())

        if "organic_results" not in results.keys():
            if filter_year_min is not None and filter_year_max is not None:
                raise Exception(
                    f"No results found for query: '{query}' with filtering on year>={filter_year_min} and year<={filter_year_max}. Use a less restrictive query or do not filter on year."
                )
            else:
                raise Exception(
                    f"No results found for query: '{query}'. Use a less restrictive query."
                )
        if len(results["organic_results"]) == 0:
            if filter_year_min is not None or filter_year_max is not None:
                year_filter_message = (
                    f" with filter year={filter_year_min} or {filter_year_max}"
                    if filter_year_min is not None or filter_year_max is not None
                    else ""
                )
                return f"No results found for '{query}'{year_filter_message}. Try with a more general query, or remove the year filter."
            else:
                return f"No results found for '{query}'. Try with a more general query."

        web_snippets = []
        if "organic_results" in results:
            for idx, page in enumerate(results["organic_results"]):
                date_published = ""
                if "date" in page:
                    date_published = "\nDate published: " + page["date"]

                source = ""
                if "source" in page:
                    source = "\nSource: " + page["source"]

                snippet = ""
                if "snippet" in page:
                    snippet = "\n" + page["snippet"]

                redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"

                redacted_version = redacted_version.replace(
                    "Your browser can't play this video.", ""
                )
                web_snippets.append(redacted_version)

        return "## Search Results\n" + "\n\n".join(web_snippets)


DEEP_RESEARCH_PROMPT_TPL = """
You are a research assistant tasked with analyzing an Arxiv paper and creating a comprehensive research report.
Your goal is to research the paper's topic, find external sources that reference it, and collect them for later use.

You will analyze the paper at: {arxiv_url}.

1. Begin by reading the Arxiv paper provided at.
   a. Read the paper thoroughly, paying attention to the main thesis, methodology, and conclusions.
   b. Identify key concepts, theories, and terminology used in the paper.

2. Explore external sources which reference this paper:
   a. Search for blog posts, articles, and academic discussions that cite the Arxiv paper URL. Make sure you fetch the pages you find most interesting.
   b. Focus on sources from Substack, Medium, and academic blogs.
   c. Collect at least 3-5 relevant external sources that provide substantial analysis or discussion of the paper.
   d. Try to find both sources that are around the time of the paper and those that are newer where they put it in context.

3. Write a report of your findings. Structure your research report as follows:
   a. Introduction: Provide an overview of the topic and its significance.
   b. Background: Offer necessary context and foundational information.
   c. Main Body: Discuss the key findings from your sources, organized by themes or subtopics.
   d. Discussion: Analyze the implications of the research, highlight any controversies or debates, and discuss potential future directions.
   e. Conclusion: Summarize the main points and provide closing thoughts.

- Use in-text citations to credit your sources. For ArXiv papers, use the format (Author et al., Year). For supplementary sources, use (Source Name, Year). Include a "References" section at the end of your report with full citations for all sources used.
- Write your research report, aiming for a comprehensive yet concise presentation of the topic. The report should be between 1000-1500 words.

Make sure code blocks are formatted correctly using py.
"""


def run_deep_paper_researcher_agent(
    url, model, stream=False, verbosity_level=LogLevel.OFF, max_steps=3
):
    collection_name = f"paper_sources_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    embedding_config = Embedding.default()
    vector_store = QdrantVectorStore.instance(
        collection_name=collection_name,
        embedding_config=embedding_config,
    )

    paper_agent = ToolCallingAgent(
        name="PaperAnalyzer",
        tools=[
            # CustomGoogleSearchTool(),
            PaperRetriever(),
        ],
        model=model,
        max_steps=4,
        description="A team member agent who can analyze Arxiv papers. Provide it with an Arxiv URL and any areas you want it to focus on.",
    )
    # paper_agent.prompt_templates["managed_agent"]["task"] += (
    #    ""
    # )

    browser_agent = ToolCallingAgent(
        name="WebBrowser",
        tools=[
            # CustomGoogleSearchTool(),
            FakeGoogleSearchTool(),
            PersistingVisitWebpageTool(vector_store, embedding_config),
        ],
        model=model,
        max_steps=4,
        description="""A team member that will search the internet to answer your question.
            Ask them for all your questions that require browsing the web.
            Provide them as much context as possible, in particular if you need to search on a specific timeframe!
            And don't hesitate to provide them with a complex search task, like finding a difference between two webpages.
            Your request must be a real sentence, not a google search! Like "Find me this information (...)" rather than a few keywords.""",
    )

    # Should we combine save and visit?
    # browser_agent.prompt_templates["managed_agent"]["task"] += (
    #    "For the most relevant results you find for the task, you should fetch the page using VisitWebpageTool."
    # )

    manager_agent = CodeAgent(
        name="Manager",
        tools=[
            # PaperRetriever(),
            # TextInspectorTool(),
        ],
        model=model,
        max_steps=max_steps,
        verbosity_level=verbosity_level,
        managed_agents=[paper_agent, browser_agent],
    )

    prompt = DEEP_RESEARCH_PROMPT_TPL.format(arxiv_url=url)
    return manager_agent.run(prompt, stream=stream)
