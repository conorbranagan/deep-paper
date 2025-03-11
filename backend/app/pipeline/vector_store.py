# stdlib
from abc import ABC, abstractmethod
from typing import Any
import logging
import uuid

# 3p
from qdrant_client import QdrantClient, models as qdrant_models
from qdrant_client.models import PointStruct
from pydantic import BaseModel

from app.pipeline.embedding import EmbeddingConfig
from app.pipeline.chunk import Chunk
from app.config import settings

log = logging.getLogger(__name__)


class VectorResult(BaseModel):
    document: str
    metadata: dict[str, Any]
    score: float


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(
        self, chunks: list[Chunk], metadata: list[dict[str, Any]]
    ) -> None:
        """Add documents to the vector store with optional metadata."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[VectorResult]:
        """Search for documents similar to the query."""
        pass


class QdrantVectorStore(VectorStore):
    """Vector store using Qdrant."""

    _instance = None

    @classmethod
    def instance(
        cls,
        collection_name: str,
        embedding_config: EmbeddingConfig,
        timeout: int = 5,
    ) -> "QdrantVectorStore":
        """Get the singleton instance of the Qdrant vector store.
        You should always use this method to avoid multiple connections causing issues.
        """
        url = settings.QDRANT_URL
        api_key = settings.QDRANT_API_KEY or None
        if cls._instance is None:
            cls._instance = cls(
                url, collection_name, embedding_config, timeout, api_key
            )
        return cls._instance

    def __init__(
        self,
        url: str,
        collection_name: str,
        embedding_config: EmbeddingConfig,
        timeout: int = 5,
        api_key: str | None = None,
    ):
        """Initialize the Qdrant vector store.
        Supports local file paths (file://path/to/data/qdrant) and remote URLs (host:port)
        """
        if url.startswith("file://"):
            self.client = QdrantClient(path=url[7:], timeout=timeout)
            log.info("using local qdrant at %s", url[7:])
        else:
            host, port = url.split(":")
            https = port == "443"
            self.client = QdrantClient(
                host=host, port=int(port), timeout=timeout, https=https, api_key=api_key
            )
            log.info("using remote qdrant at %s:%s", host, port)

        self.embedding_fn = embedding_config.embedding_fn
        self.collection_name = f"{collection_name}-{embedding_config.name}"

        # Create the collection if it doesn't exist
        existing_collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.collection_name not in existing_collections:
            log.info(f"Creating collection {self.collection_name}")
            self.client.create_collection(
                self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=embedding_config.size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def add_documents(
        self, chunks: list[Chunk], metadata: list[dict[str, Any]]
    ) -> None:
        """Add documents to the vector store."""
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=self.embedding_fn(str(doc)),
                payload={
                    "metadata": {"chunk_id": doc.chunk_id, **meta},
                    "document": doc.text,
                },
            )
            for doc, meta in zip(chunks, metadata)
        ]
        self.client.upsert(self.collection_name, points)

    def search(self, query: str, top_k: int = 5) -> list[VectorResult]:
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
                VectorResult(
                    document=point.payload["document"],
                    metadata=point.payload["metadata"],
                    score=point.score,
                )
            )
        return results
