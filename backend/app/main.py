from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import research

app = FastAPI(title="LLM Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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