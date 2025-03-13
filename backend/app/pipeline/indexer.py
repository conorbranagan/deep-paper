"""
Indexing pipeline for papers.
"""

from app.pipeline.chunk import ChunkingStrategy
from app.models.paper import Paper
from app.pipeline.vector_store import VectorStore
from app.pipeline.embedding import EmbeddingConfig
from app.pipeline.chunk import AdaptiveChunker


class PaperIndexer:
    """Class to index papers using a chunking strategy and vector store."""

    def __init__(
        self,
        chunking_strategy: ChunkingStrategy,
        embedding_config: EmbeddingConfig,
        vector_store: VectorStore,
    ):
        self.chunker = AdaptiveChunker(chunking_strategy, embedding_config)
        self.vector_store = vector_store

    def index_paper(self, paper: Paper) -> None:
        """Index a paper using the chunking strategy and vector store."""
        chunks = self.chunker.chunk(paper)
        metadata = [
            {
                "id": f"{paper.arxiv_id}-{i}",
                "paper_title": paper.latex.title,
                "paper_id": paper.arxiv_id,
                "chunk_idx": i,
            }
            for i in range(len(chunks))
        ]
        self.vector_store.add_documents(chunks, metadata)
