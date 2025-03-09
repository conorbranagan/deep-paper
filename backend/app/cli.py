import argparse
import sys
from abc import ABC, abstractmethod
from colorama import Fore, Style, init as colorama_init

from app.models.paper import Paper, PaperNotFound
from app.agents.summarizer import summarize_paper, summarize_topic
from app.agents.researcher import run_paper_agent, run_research_agent
from app.pipeline.indexer import PaperIndexer
from app.pipeline.chunk import SectionChunkingStrategy
from app.pipeline.vector_store import QdrantVectorStore, VectorStore, QdrantVectorConfig
from app.config import settings, AVAILABLE_MODELS
from ddtrace.llmobs import LLMObs

from smolagents.monitoring import LogLevel

colorama_init()


class Command(ABC):
    """Base class for all CLI commands."""

    @classmethod
    @abstractmethod
    def setup_parser(cls, subparsers):
        """Set up the argument parser for this command."""
        pass

    @abstractmethod
    def execute(self, args):
        """Execute the command with the given arguments."""
        pass


class ParseCommand(Command):
    """Command to parse a paper and print its structure."""

    @classmethod
    def setup_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "parse", help="Parse a paper and print its structure"
        )
        parser.add_argument(
            "-u", "--url", type=str, required=True, help="URL of the paper to parse"
        )
        return parser

    def execute(self, args):
        paper = Paper.from_url(args.url)
        paper.print_tree()


class SummarizeCommand(Command):
    """Command to analyze and summarize academic papers."""

    @classmethod
    def setup_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "summarize", help="Analyze and summarize academic papers"
        )
        paper_subparsers = parser.add_subparsers(dest="summarize_command")

        # Summarize subcommand
        summarize_parser = paper_subparsers.add_parser(
            "all", help="Summarize an academic paper"
        )
        summarize_parser.add_argument(
            "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
        )
        summarize_parser.add_argument(
            "-m",
            "--model",
            choices=AVAILABLE_MODELS,
            default=settings.DEFAULT_MODEL,
            help="Model to use for summarization",
        )

        # Topic subcommand
        topic_parser = paper_subparsers.add_parser(
            "topic", help="Summarize an academic paper for a specific topic"
        )
        topic_parser.add_argument(
            "-u", "--url", type=str, required=True, help="URL of the paper to summarize"
        )
        topic_parser.add_argument(
            "-t", "--topic", type=str, required=True, help="Topic to focus on"
        )
        topic_parser.add_argument(
            "-m",
            "--model",
            choices=AVAILABLE_MODELS,
            default=settings.DEFAULT_MODEL,
            help="Model to use for summarization",
        )

        return parser

    def execute(self, args):
        if not hasattr(args, "summarize_command") or args.summarize_command is None:
            print("Please specify a paper command (all or topic)")
            return

        paper = Paper.from_url(args.url)
        if args.summarize_command == "all":
            summary = summarize_paper(paper, model=args.model)
            print(f"Paper Summary: {paper.latex.title}")
            print(f"\nAbstract:\n{summary.abstract}")
            print(f"\nSummary:\n{summary.summary}")
            print("\nTopics:")
            for topic in summary.topics:
                print(f"- {topic.topic}: {topic.summary}")
                print("  Further Reading:")
                for fr in topic.further_reading:
                    print(f"  - {fr.title}: {fr.author}, {fr.url}")

        elif args.summarize_command == "topic":
            for chunk in summarize_topic(paper, args.topic, model=args.model):
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="")
            print("\n")


class ResearchCommand(Command):
    """Command to research a paper with an AI agent."""

    @classmethod
    def setup_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "research", help="Research a paper with an AI agent"
        )
        parser.add_argument(
            "-u",
            "--url",
            type=str,
            required=False,
            help="URL for paper, optional if you want to research a specific paper",
        )
        parser.add_argument("prompt", help="Prompt for researching")
        parser.add_argument(
            "-m",
            "--model",
            choices=AVAILABLE_MODELS,
            default=settings.DEFAULT_MODEL,
            help="Model to use for research",
        )
        return parser

    def execute(self, args):
        LLMObs.enable(ml_app="deep-paper")
        agent_model = settings.agent_model(args.model, 0.2)
        if args.url:
            run_paper_agent(
                args.url,
                args.prompt,
                agent_model,
                stream=False,
                verbosity_level=LogLevel.INFO,
            )
        else:
            run_research_agent(
                args.prompt, agent_model, stream=False, verbosity_level=LogLevel.INFO
            )


class PipelineCommand(Command):
    """Commands for the indexing and querying pipeline."""

    @classmethod
    def setup_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "pipeline", help="Index papers and run test queries"
        )
        subcommands = parser.add_subparsers(
            dest="pipeline_command", help="Pipeline subcommands"
        )

        # Index subcommand
        index_parser = subcommands.add_parser(
            "index", help="Index papers from a file of arxiv IDs"
        )
        index_parser.add_argument(
            "--ids-file",
            "-i",
            type=str,
            default="data/ids.txt",
            help="File containing arxiv ids, one per line",
        )
        index_parser.add_argument(
            "--embedding",
            "-e",
            choices=["bert", "openai"],
            default="bert",
            help="Embedding function to use",
        )
        index_parser.add_argument(
            "--vector-store",
            "-s",
            choices=["qdrant"],
            default="qdrant",
            help="Vector store to use",
        )

        # Query subcommand
        query_parser = subcommands.add_parser(
            "query", help="Run test queries against the indexed papers"
        )
        query_parser.add_argument(
            "--queries-file",
            "-q",
            type=str,
            default="data/queries.txt",
            help="File containing queries, one per line",
        )
        query_parser.add_argument(
            "--top-k",
            "-k",
            type=int,
            default=5,
            help="Top K results to return for each query",
        )
        query_parser.add_argument(
            "--embedding",
            "-e",
            choices=["bert", "openai"],
            default="bert",
            help="Embedding function to use",
        )
        query_parser.add_argument(
            "--vector-store",
            "-s",
            choices=["qdrant"],
            default="qdrant",
            help="Vector store to use",
        )

        return parser

    def execute(self, args):
        if not hasattr(args, 'pipeline_command') or args.pipeline_command is None:
            print("Please specify a subcommand: index or query")
            return

        vector_store: VectorStore
        if args.vector_store == "qdrant":
            vector_config: QdrantVectorConfig
            if args.embedding == "bert":
                vector_config = QdrantVectorConfig.bert_384("papers")
            elif args.embedding == "openai":
                vector_config = QdrantVectorConfig.openai_ada_002("papers")
            else:
                raise ValueError(f"Invalid embedding function: {args.embedding}")
            vector_store = QdrantVectorStore(
                url=settings.QDRANT_URL,
                config=vector_config,
            )
        else:
            raise ValueError(f"Invalid vector store: {args.vector_store}")

        if args.pipeline_command == "index":
            self._index_papers(args, vector_store)
        elif args.pipeline_command == "query":
            self._run_queries(args, vector_store)

    def _index_papers(self, args, vector_store):
        chunking_strategy = SectionChunkingStrategy()
        indexer = PaperIndexer(chunking_strategy, vector_store)

        # Load and index papers
        papers = []
        with open(args.ids_file, "r") as f:
            for line in f:
                arxiv_id = line.strip()
                if arxiv_id.startswith("#"):
                    continue

                print(f"Analyzing paper {arxiv_id}")
                try:
                    paper = Paper.from_arxvid_id(arxiv_id)
                    papers.append(paper)

                    # Index the paper
                    print(f"Indexing paper {paper.arxiv_id}")
                    indexer.index_paper(paper)
                except PaperNotFound:
                    print(f"{Fore.RED}Paper not found: {arxiv_id}{Style.RESET_ALL}")

    def _run_queries(self, args, vector_store):
        # Run test queries
        print(f"\n{Fore.CYAN}=== QUERIES ==={Style.RESET_ALL}\n")
        with open(args.queries_file, "r") as f:
            test_queries = [line.strip() for line in f]

        for query in test_queries:
            print(f"{Fore.GREEN}Query: '{query}'{Style.RESET_ALL}")
            results = vector_store.search(query, top_k=args.top_k)

            if results:
                print(f"{Fore.YELLOW}Top {len(results)} results:{Style.RESET_ALL}")
                for i, result in enumerate(results):
                    paper_id = result["metadata"].get("paper_id", "Unknown")
                    paper_title = result["metadata"].get("paper_title", "Unknown")
                    score = result["score"]
                    print(
                        f"{Fore.BLUE}{i+1}. Paper ID: {paper_id} (Score: {score:.4f}){Style.RESET_ALL}"
                    )
                    print(
                        f"{Fore.WHITE}   Title: {paper_title} (Score: {score:.4f}){Style.RESET_ALL}"
                    )
                    print(
                        f"{Fore.WHITE}   Excerpt: {result['document'][:150]}...{Style.RESET_ALL}\n"
                    )
            else:
                print(f"{Fore.RED}No results found.{Style.RESET_ALL}")

            print(f"{Fore.MAGENTA}{'-' * 50}{Style.RESET_ALL}")

class CLI:
    """Main CLI class that manages all commands."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Paper analyzer cli")
        self.subparsers = self.parser.add_subparsers(
            dest="command", help="Available commands"
        )

        # Register all commands
        self.commands = {
            "parse": ParseCommand(),
            "summarize": SummarizeCommand(),
            "research": ResearchCommand(),
            "pipeline": PipelineCommand(),
        }

        # Set up parsers for all commands
        for _, command in self.commands.items():
            command.setup_parser(self.subparsers)

    def run(self):
        """Parse arguments and execute the appropriate command."""
        args = self.parser.parse_args()

        if args.command is None:
            self.parser.print_help()
            sys.exit(1)

        if args.command in self.commands:
            self.commands[args.command].execute(args)
        else:
            print(f"Unknown command: {args.command}")
            self.parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    cli = CLI()
    cli.run()
