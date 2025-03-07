"""
Indexing pipeline for papers.
"""

from app.pipeline.chunk import ChunkingStrategy
from app.models.paper import Paper
from app.pipeline.vector_store import VectorStore

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

