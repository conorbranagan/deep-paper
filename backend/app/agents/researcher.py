from app.models.paper import Paper, PaperNotFound

from smolagents import Tool, CodeAgent, MultiStepAgent, FinalAnswerTool, UserInputTool, GoogleSearchTool, DuckDuckGoSearchTool
from smolagents.agent_types import AgentText, AgentImage, AgentAudio
from smolagents.monitoring import LogLevel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever
from ddtrace.llmobs import LLMObs

from app.pipeline.vector_store import VectorStore, QdrantVectorStore
from app.pipeline.embedding import EmbeddingFunction


def wrap_tool(cls):
    original_forward = cls.forward

    def wrapped_forward(self, *args, **kwargs):
        with LLMObs.tool(self.name):
            tool_meta = {k: v for k, v in kwargs.items()}
            LLMObs.annotate(metadata=tool_meta)
            return original_forward(self, *args, **kwargs)

    cls.skip_forward_signature_validation = True
    cls.forward = wrapped_forward


def wrap_agent(cls):
    original_step = cls.step
    original_planning_step = cls.planning_step
    original_final_answer = cls.provide_final_answer
    original_run = cls.run

    def wrapped_step(self, memory_step):
        with LLMObs.task(name="action"):
            res = original_step(self, memory_step)
            step_meta = memory_step.dict()
            annotate_args = dict(
                input_data=step_meta.pop("model_input_messages"),
                output_data=step_meta.pop("model_output_message"),
                metadata=step_meta,
            )
            LLMObs.annotate(**annotate_args)
            return res

    def wrapped_planning_step(self, *args, **kwargs):
        with LLMObs.task(name="planning"):
            return original_planning_step(self, *args, **kwargs)

    def wrapped_final_answer(self, *args, **kwargs):
        with LLMObs.task(name="final_answer"):
            answer = original_final_answer(self, *args, **kwargs)
            LLMObs.annotate(
                input_data=args[0] if len(args) > 0 else "",
                output_data=answer,
            )
            return answer

    def wrapped_run(self, *args, **kwargs):
        llmbos_metadata = {
            "task": args[0] or kwargs.get("task") or "unset task",
            "max_steps": kwargs.get("max_steps"),
            "stream": kwargs.get("stream"),
            "reset": kwargs.get("reset"),
            # other options: images, additional_args
        }
        is_stream = kwargs.get("stream", False)
        if is_stream:
            return _wrapped_run_stream(self, *args, llmbos_metadata=llmbos_metadata, **kwargs)
        else:
            # For non-stream we simply return that's provided.
            with LLMObs.agent("smolagents_agent"):
                output = original_run(self, *args, **kwargs)
                LLMObs.annotate(
                    input_data=llmbos_metadata["task"],
                    output_data=output,
                    metadata=llmbos_metadata,
                )
                return output

    def _wrapped_run_stream(self, *args, llmbos_metadata, **kwargs):
        # When it's a stream we have to wrap the generator. We pick the last
        # value to come out as our potential output and cast it to str if it's a known type.
        with LLMObs.agent("smolagents_agent"):
            r_gen = original_run(self, *args, **kwargs)
            output = "unknown"
            last_val = None
            for val in r_gen:
                last_val = val
                yield val

            # Handle specific types for now.
            if last_val and isinstance(last_val, (AgentText, AgentImage, AgentAudio)):
                output = last_val.to_string()
                LLMObs.annotate(
                    input_data=llmbos_metadata["task"],
                    output_data=output,
                    metadata=llmbos_metadata,
                )

    cls.step = wrapped_step
    cls.planning_step = wrapped_planning_step
    cls.provide_final_answer = wrapped_final_answer
    cls.run = wrapped_run


wrap_agent(CodeAgent)
wrap_agent(MultiStepAgent)


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


wrap_tool(PaperRetriever)
wrap_tool(PaperChunkRetriever)
wrap_tool(CitationRetriever)
wrap_tool(FinalAnswerTool)
wrap_tool(UserInputTool)
wrap_tool(GoogleSearchTool)
wrap_tool(DuckDuckGoSearchTool)


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
        embedding_fn=EmbeddingFunction.sbert_mini_lm, collection_name="papers"
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
