# stdlib
from abc import ABC, abstractmethod
from typing import Any, Callable
import logging
import uuid

# 3p
from qdrant_client import QdrantClient, models as qdrant_models
from qdrant_client.models import PointStruct
from pydantic import BaseModel

from app.pipeline.embedding import EmbeddingFunction

log = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_documents(
        self, documents: list[str], metadata: list[dict[str, Any]]
    ) -> None:
        """Add documents to the vector store with optional metadata."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for documents similar to the query."""
        pass

class QdrantVectorConfig(BaseModel):
    embedding_fn: Callable[[str], list[float]]
    vector_params: qdrant_models.VectorParams
    collection_name: str

    @classmethod
    def default(cls, collection_name: str):
        # Currently defaulting to OpenAI because loading BeRT model in prod uses too much memory.
        return cls.openai_ada_002(collection_name)

    @classmethod
    def bert_384(cls, collection_name: str):
        log.info("using openai ada 002 embedding function")
        return cls(
            embedding_fn=EmbeddingFunction.sbert_mini_lm,
            vector_params=qdrant_models.VectorParams(
                size=384,
                distance=qdrant_models.Distance.COSINE,
            ),
            collection_name=f"{collection_name}-bert-384",
        )
    
    @classmethod
    def openai_ada_002(cls, collection_name: str):
        log.info("using openai ada 002 embedding function")
        return cls(
            embedding_fn=EmbeddingFunction.openai_ada_002,
            vector_params=qdrant_models.VectorParams(
                size=1536,
                distance=qdrant_models.Distance.COSINE,
            ),
            collection_name=f"{collection_name}-openai-ada-002",
        )

class QdrantVectorStore(VectorStore):
    """Vector store using Qdrant."""

    def __init__(self, url: str, config: QdrantVectorConfig):
        """Initialize the Qdrant vector store.
        Supports local file paths (file://path/to/data/qdrant) and remote URLs (host:port)
        """
        if url.startswith("file://"):
            self.client = QdrantClient(path=url[7:])
            log.info("using local qdrant at %s", url[7:])
        else:
            host, port = url.split(":")
            self.client = QdrantClient(host=host, port=int(port))
            log.info("using remote qdrant at %s:%s", host, port)

        self.embedding_fn = config.embedding_fn
        self.collection_name = config.collection_name

        # Create the collection if it doesn't exist
        existing_collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.collection_name not in existing_collections:
            log.info(f"Creating collection {self.collection_name}")
            self.client.create_collection(
                self.collection_name,
                vectors_config=config.vector_params,
            )

    def add_documents(
        self, documents: list[str], metadata: list[dict[str, Any]]
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

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
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
