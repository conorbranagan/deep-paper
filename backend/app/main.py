from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.routers import research, indexing
from app.config import init_config


init_config()

app = FastAPI(title="Paper Research Assistant API")
FastAPIInstrumentor.instrument_app(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # FIXME: Probably be more specific.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, tags=["research"])
app.include_router(indexing.router, tags=["indexing"])


# Dependency to access current span from FastAPI routes
def get_current_span():
    return trace.get_current_span()


@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Agent API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
