from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.model_service import ModelService
from app.routes import moderation

model_service = ModelService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading model...")
    model_service.load()
    print("Model ready.")
    yield
    print("Shutting down.")

app = FastAPI(
    title="Chat Moderator API",
    description="Real-time chat message moderation using XLM-RoBERTa",
    version="1.0.0",
    lifespan=lifespan
)

app.state.model_service = model_service
app.include_router(moderation.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model_service.is_loaded}
