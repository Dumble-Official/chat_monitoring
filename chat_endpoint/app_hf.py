"""
HuggingFace Space entry point.
The Space must have these Secrets configured:
  - MONGO_URI
  - JWT_SECRET
  - HF_MODEL_REPO   (e.g. your-username/xlmroberta-chat-moderator)
"""
import uvicorn
from app.main import app          # noqa: F401  (imported for HF to detect FastAPI app)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=False)
