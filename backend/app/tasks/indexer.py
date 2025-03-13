import logging
import queue
import sys
from datetime import datetime

import modal

from app.models.paper import Paper
from app.pipeline.indexer import PaperIndexer
from app.pipeline.chunk import SectionChunkingStrategy
from app.pipeline.embedding import Embedding
from app.pipeline.vector_store import QdrantVectorStore

log = logging.getLogger(__name__)

deps = [
    "pydantic>=2.10.6",
    "bibtexparser>=1.4.3",
    "pylatexenc>=3.0a32",
    "requests>=2.32.3",
    "qdrant-client>=1.13.3",
    "ddtrace>=3.2.1",
    "openai>=1.65.2",
    "pymupdf>=1.25.3",
    "smolagents[transformers]>=1.9.2",
    "torch>=2.6.0",
    "tiktoken>=0.9.0",
    "litellm>=1.61.20",
]


# UV Version is faster (but not working?)
# image = (
#   modal.Image.debian_slim()
#   .pip_install("uv")
#   .run_commands("uv -v pip install --system --compile-bytecode {}".format(" ".join(deps)))
# )

image = (
    modal.Image.debian_slim()
    .pip_install(deps)
    .env(
        dict(
            # For Modal functions we need to use the public URL
            QDRANT_URL="qdrant-production-4336.up.railway.app:443",
        )
    )
)

job_queue = modal.Queue.from_name("indexer-job-queue", create_if_missing=True)
app = modal.App(image=image, name="paper_indexer")


def get_indexer() -> PaperIndexer:
    embedding_config = Embedding.default()
    vector_store = QdrantVectorStore.instance(
        collection_name=QdrantVectorStore.PAPERS_COLLECTION,
        embedding_config=embedding_config,
    )
    return PaperIndexer(
        chunking_strategy=SectionChunkingStrategy(),
        embedding_config=embedding_config,
        vector_store=vector_store,
    )


@app.function(secrets=[modal.Secret.from_name("qdrant-api-key")])
def index_single(url: str):
    try:
        s = datetime.now()
        indexer = get_indexer()
        indexer.index_paper(Paper.from_url(url))
        print(f"Crawled: {url} in {datetime.now() - s}")
    except Exception as exc:
        print(
            f"Failed to index paper {url} with error {exc}, skipping...",
            file=sys.stderr,
        )


@app.function(secrets=[modal.Secret.from_name("qdrant-api-key")])
def index_batch(urls: list[str]) -> None:
    s = datetime.now()
    indexer = get_indexer()
    for url in urls:
        try:
            indexer.index_paper(Paper.from_url(url))
            print(f"Indexed: {url}")
        except Exception as exc:
            print(
                f"Failed to index paper {url} with error {exc}, skipping...",
                file=sys.stderr,
            )

    print(f"Crawled: {len(urls)} papers in {datetime.now() - s}")


@app.function(timeout=600)
def papers_crawler(urls: list[str]):
    start_time = datetime.now()

    calls = []
    job_queue.put_many(urls)

    visited: set[str] = set([])
    per_spawn = 50

    # Crawl until the queue is empty
    while True:
        try:
            next_urls = job_queue.get_many(per_spawn, timeout=5)
        except queue.Empty:
            break
        visited |= set(next_urls)
        calls.append(index_batch.spawn(list(next_urls)))

    # Wait for all the calls to finish
    for call in calls:
        call.get()

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"Crawled {len(visited)} URLs in {elapsed:.2f} seconds")


@app.local_entrypoint()
def main():
    # Test entrypoint for local development
    urls = [
        "https://arxiv.org/abs/2309.15217",
        "https://arxiv.org/abs/2206.05802",
        "https://arxiv.org/abs/2204.14146",
        "https://arxiv.org/abs/1810.08575",
        "https://arxiv.org/abs/2204.14146",
        "https://arxiv.org/abs/2009.01325",
        "https://arxiv.org/abs/2005.14165",
        "https://arxiv.org/abs/2009.03300",
    ]
    papers_crawler.remote(urls)
