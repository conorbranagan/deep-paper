from app.celery_app import celery_app
from app.models.paper import Paper, PaperNotFound
from app.pipeline.indexer import PaperIndexer
from app.pipeline.chunk import SectionChunkingStrategy
from app.pipeline.vector_store import QdrantVectorStore, QdrantVectorConfig
from app.config import settings

from celery.utils.log import get_task_logger


log = get_task_logger(__name__)


@celery_app.task(bind=True, name="index_paper")
def index_paper(self, arxiv_id: str):
    """
    Celery task to index a paper by its arxiv ID

    Args:
        self: The Celery task instance
        arxiv_id: The arxiv ID of the paper to index

    Returns:
        dict: Status information about the indexing job
    """
    log.info(f"Starting indexing job for paper {arxiv_id}")

    try:
        # Update task state to STARTED
        self.update_state(state="STARTED", meta={"arxiv_id": arxiv_id, "progress": 0})

        # Initialize vector store
        vector_config = QdrantVectorConfig.default("papers")
        vector_store = QdrantVectorStore(
            url=settings.QDRANT_URL,
            config=vector_config,
        )

        # Initialize indexer
        chunking_strategy = SectionChunkingStrategy()
        indexer = PaperIndexer(chunking_strategy, vector_store)

        # Fetch the paper
        log.info(f"Fetching paper {arxiv_id}")
        paper = Paper.from_arxvid_id(arxiv_id)

        # Update progress
        self.update_state(
            state="PROCESSING", meta={"arxiv_id": arxiv_id, "progress": 0.3}
        )

        # Index the paper
        log.info(f"Indexing paper {arxiv_id}")
        indexer.index_paper(paper)

        # Update progress
        self.update_state(
            state="FINALIZING", meta={"arxiv_id": arxiv_id, "progress": 0.9}
        )

        # Return success result
        log.info(f"Successfully indexed paper {arxiv_id}")
        return {
            "status": "completed",
            "arxiv_id": arxiv_id,
            "title": (
                paper.latex.title
                if hasattr(paper, "latex") and paper.latex
                else "Unknown"
            ),
            "progress": 1.0,
        }

    except PaperNotFound:
        log.error(f"Paper not found: {arxiv_id}")
        return {
            "status": "error",
            "arxiv_id": arxiv_id,
            "error": f"Paper with arxiv ID {arxiv_id} not found",
        }
    except Exception as e:
        log.exception(f"Error indexing paper {arxiv_id}: {str(e)}")
        return {"status": "error", "arxiv_id": arxiv_id, "error": str(e)}


@celery_app.task(bind=True, name="index_papers_batch")
def index_papers_batch(self, arxiv_ids: list):
    """
    Celery task to index multiple papers

    Args:
        self: The Celery task instance
        arxiv_ids: List of arxiv IDs to index

    Returns:
        dict: Status information about the batch indexing job
    """
    results = []
    total = len(arxiv_ids)

    for i, arxiv_id in enumerate(arxiv_ids):
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i,
                "total": total,
                "progress": i / total,
                "arxiv_id": arxiv_id,
            },
        )

        # Queue individual paper indexing task
        result = index_paper.delay(arxiv_id)
        results.append({"arxiv_id": arxiv_id, "task_id": result.id})

    return {"status": "completed", "total": total, "tasks": results}
