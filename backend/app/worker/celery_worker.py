from app.celery_app import celery_app
from app.tasks.indexing import index_paper, index_papers_batch

# Register tasks
celery_app.tasks.register(index_paper)
celery_app.tasks.register(index_papers_batch)

# This is the entry point for the Celery worker
if __name__ == "__main__":
    celery_app.start()
