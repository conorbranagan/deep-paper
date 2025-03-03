import argparse
import os

from app.models.paper import Paper, PaperNotFound

from smolagents import Tool, CodeAgent, LiteLLMModel
from smolagents import TransformersModel
from smolagents.monitoring import LogLevel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever


class PaperRetriever(Tool):
    name = "paper_retriever"
    description = "Fetch a paper by the arxiv id"
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
            contents = "\n".join(lf.as_text for lf in paper.contents)
            return f"\nPaper Contents\n\n{contents}"

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


prompt_tpl = """
You are researching the paper at this URL: {url}

{prompt}
"""


def run(url, prompt, model, stream=False, verbosity_level=LogLevel.OFF):
    agent = CodeAgent(
        tools=[
            PaperRetriever(),
        ],
        model=model,
        max_steps=3,
        verbosity_level=verbosity_level,
    )

    system_prompt = prompt_tpl.format(
        url=url,
        prompt=prompt,
    )

    return agent.run(system_prompt, stream=stream)    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="paper researcher")
    parser.add_argument("url", help="URL for paper (either PDF or Arxiv link)")
    parser.add_argument("prompt", help="Prompt for researching this paper")
    parser.add_argument(
        "-m", "--model", choices=["claude", "gpt-4o-mini", "local-32b", "local-8b"], default="gpt-4o-mini"
    )
    args = parser.parse_args()

    if args.model == "local-32b":
        model = TransformersModel(
            model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
            max_new_tokens=4096,
            device_map="auto",
        )
    elif args.model == "local-8b":
        model = TransformersModel(
            model_id="NousResearch/DeepHermes-3-Llama-3-8B-Preview",
            max_new_tokens=4096,
            device_map="auto",
        )
    elif args.model == "claude":
        model = LiteLLMModel(
            "anthropic/claude-3-7-sonnet-latest",
            temperature=0.2,
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )
    elif args.model == "gpt-4o-mini":
        model = LiteLLMModel(
            "openai/gpt-4o-mini",
            temperature=0.2,
            api_key=os.environ["OPENAI_API_KEY"],
        )
    else:
        raise Exception(f"unknown model: {args.model}")

    Paper.from_arxvid_id("2206.05802")

    run(args.url, args.prompt, model, stream=False, verbosity_level=LogLevel.DEBUG)
