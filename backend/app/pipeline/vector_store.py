# stdlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any

# 3p
import numpy as np


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(
        self, documents: List[str], metadata: List[Dict[str, Any]] = None
    ) -> None:
        """Add documents to the vector store with optional metadata."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query."""
        pass


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store using cosine similarity."""

    def __init__(self, embedding_fn):
        """
        Initialize the in-memory vector store.

        Args:
            embedding_fn: Function that converts text to embeddings.
                          If None, OpenAI embeddings will be used.
        """
        self.documents = []
        self.metadata = []
        self.embeddings = []
        self.embedding_fn = embedding_fn

    def add_documents(
        self, documents: List[str], metadata: List[Dict[str, Any]] = None
    ) -> None:
        """Add documents to the vector store."""
        if metadata is None:
            metadata = [{} for _ in documents]

        for doc, meta in zip(documents, metadata):
            self.documents.append(doc)
            self.metadata.append(meta)
            self.embeddings.append(self.embedding_fn(doc))

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query."""
        if not self.documents:
            return []

        query_embedding = self.embedding_fn(query)

        # Calculate cosine similarity
        similarities = []
        for doc_embedding in self.embeddings:
            # Normalize both vectors
            doc_norm = np.linalg.norm(doc_embedding)
            query_norm = np.linalg.norm(query_embedding)
            similarity = np.dot(query_embedding, doc_embedding) / (
                doc_norm * query_norm
            )
            similarities.append(similarity)

        # Get top-k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append(
                {
                    "document": self.documents[idx],
                    "metadata": self.metadata[idx],
                    "score": similarities[idx],
                }
            )

        return results
