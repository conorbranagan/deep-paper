# stdlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import logging
import uuid

# 3p
import numpy as np
from qdrant_client import QdrantClient, models as qdrant_models
from qdrant_client.models import PointStruct

log = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(
        self, documents: List[str], metadata: List[Dict[str, Any]]
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
        self, documents: List[str], metadata: List[Dict[str, Any]]
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


class QdrantVectorStore(VectorStore):
    """Vector store using Qdrant."""

    # Make the default path data/qdrant relative to the project root
    DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qdrant")

    def __init__(self, embedding_fn, collection_name: str, path: str = DEFAULT_PATH):
        """Initialize the Qdrant vector store."""
        self.client = QdrantClient(path=path)
        self.embedding_fn = embedding_fn
        self.collection_name = collection_name

        # Create the collection if it doesn't exist
        existing_collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.collection_name not in existing_collections:
            log.info(f"Creating collection {self.collection_name}")
            self.client.create_collection(
                self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    # FIXME: Embedding size just matching BeRT
                    size=384, distance=qdrant_models.Distance.COSINE
                ),
            )

    def add_documents(
        self, documents: List[str], metadata: List[Dict[str, Any]]
    ) -> None:
        """Add documents to the vector store."""
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=self.embedding_fn(doc),
                payload={"metadata": meta, "document": doc},
            )
            for doc, meta in zip(documents, metadata)
        ]
        self.client.upsert(self.collection_name, points)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query."""
        query_embedding = self.embedding_fn(query)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
        )
        results = []
        for point in response.points:
            if point.payload is None:
                continue
            results.append(
                {
                    "document": point.payload["document"],
                    "metadata": point.payload["metadata"],
                    "score": point.score,
                }
            )
        return results
