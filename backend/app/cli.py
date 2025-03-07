import argparse
import sys
from abc import ABC, abstractmethod
from colorama import Fore, Style, init as colorama_init

from app.models.paper import Paper, PaperNotFound
from app.agents.summarizer import summarize_paper, summarize_topic
from app.agents.researcher import run_paper_agent, run_research_agent
from app.pipeline.indexer import PaperIndexer
from app.pipeline.chunk import SectionChunkingStrategy
from app.pipeline.vector_store import InMemoryVectorStore, QdrantVectorStore
from app.pipeline.embedding import EmbeddingFunction
from app.config import settings, AVAILABLE_MODELS

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
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Enable verbose output"
        )
        return parser

    def execute(self, args):
        agent_model = settings.agent_model(args.model, 0.2)
        verbosity = LogLevel.INFO if args.verbose else LogLevel.OFF
        if args.url:
            run_paper_agent(
                args.url,
                args.prompt,
                agent_model,
                stream=False,
                verbosity_level=verbosity,
            )
        else:
            run_research_agent(
                args.prompt, agent_model, stream=False, verbosity_level=verbosity
            )


class IndexCommand(Command):
    """Command to index papers and run test queries."""

    @classmethod
    def setup_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "index", help="Index papers and run test queries"
        )
        parser.add_argument(
            "--ids-file",
            "-i",
            type=str,
            default="data/ids.txt",
            help="File containing arxiv ids, one per line",
        )
        parser.add_argument(
            "--queries-file",
            "-q",
            type=str,
            default="data/queries.txt",
            help="File containing queries, one per line",
        )
        parser.add_argument(
            "--top-k",
            "-k",
            type=int,
            default=5,
            help="Top K results to return for each query",
        )
        parser.add_argument(
            "--embedding",
            "-e",
            choices=["bert", "openai"],
            default="bert",
            help="Embedding function to use",
        )
        parser.add_argument(
            "--vector-store",
            "-s",
            choices=["in-memory", "qdrant"],
            default="in-memory",
            help="Vector store to use",
        )
        return parser

    def execute(self, args):
        chunking_strategy = SectionChunkingStrategy()

        if args.embedding == "bert":
            embedding_fn = EmbeddingFunction.sbert_mini_lm
        elif args.embedding == "openai":
            embedding_fn = EmbeddingFunction.openai_ada_002
        else:
            raise ValueError(f"Invalid embedding function: {args.embedding}")

        if args.vector_store == "in-memory":
            vector_store = InMemoryVectorStore(embedding_fn=embedding_fn)
        elif args.vector_store == "qdrant":
            vector_store = QdrantVectorStore(
                embedding_fn=embedding_fn, collection_name="papers"
            )
        else:
            raise ValueError(f"Invalid vector store: {args.vector_store}")
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
            "index": IndexCommand(),
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
