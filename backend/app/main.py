from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import research

from ddtrace import patch_all
from app.config import init_config

# Initialize ddtrace patching
patch_all()

init_config()

app = FastAPI(title="Paper Research Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # FIXME: Probably be more specific.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, tags=["research"])

@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Agent API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)