"""
Indexing pipeline for papers.
"""

import argparse
from colorama import Fore, Style, init as colorama_init

from app.pipeline.chunk import ChunkingStrategy, SectionChunkingStrategy
from app.models.paper import Paper
from app.pipeline.vector_store import VectorStore, InMemoryVectorStore
from app.pipeline.embedding import EmbeddingFunction

colorama_init()


class PaperIndexer:
    """Class to index papers using a chunking strategy and vector store."""

    def __init__(self, chunking_strategy: ChunkingStrategy, vector_store: VectorStore):
        self.chunking_strategy = chunking_strategy
        self.vector_store = vector_store

    def index_paper(self, paper: Paper) -> None:
        """Index a paper using the chunking strategy and vector store."""
        chunks = self.chunking_strategy.chunk(paper)
        metadata = [
            {
                "paper_title": paper.latex.title,
                "paper_id": paper.arxiv_id,
                "chunk_idx": i,
            }
            for i in range(len(chunks))
        ]
        self.vector_store.add_documents(chunks, metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ids_file",
        "-i",
        type=str,
        default="ids.txt",
        help="File containing arxiv ids, one per line",
    )
    parser.add_argument(
        "--queries_file",
        "-q",
        type=str,
        default="queries.txt",
        help="File containing queries, one per line",
    )
    parser.add_argument(
        "--top_k",
        "-k",
        type=int,
        default=5,
        help="Top K results to return for each query",
    )
    parser.add_argument(
        "--embedding_fn",
        "-e",
        choices=["bert", "openai"],
        default="bert",
        help="Embedding function to use",
    )
    args = parser.parse_args()

    chunking_strategy = SectionChunkingStrategy()

    if args.embedding_fn == "bert":
        embedding_fn = EmbeddingFunction.sbert_mini_lm
    elif args.embedding_fn == "openai":
        embedding_fn = EmbeddingFunction.openai_ada_002
    else:
        raise ValueError(f"Invalid embedding function: {args.embedding_fn}")

    vector_store = InMemoryVectorStore(embedding_fn=embedding_fn)
    indexer = PaperIndexer(chunking_strategy, vector_store)

    # Load and index papers
    papers = []
    with open(args.ids_file, "r") as f:
        for line in f:
            arxiv_id = line.strip()
            if arxiv_id.startswith("#"):
                continue

            print(f"Analyzing paper {arxiv_id}")
            paper = Paper.from_arxvid_id(arxiv_id)
            papers.append(paper)

            # Index the paper
            print(f"Indexing paper {paper.arxiv_id}")
            indexer.index_paper(paper)

    # Run some test queries
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
