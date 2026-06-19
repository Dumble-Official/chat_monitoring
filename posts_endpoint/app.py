import os
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import XLMRobertaTokenizer, XLMRobertaForSequenceClassification
from huggingface_hub import login
import uvicorn

# ─────────────────────────────────────────
#  Config
# ─────────────────────────────────────────
MODEL_NAME = os.getenv("MODEL_NAME", "smaaanwerb/posts")  
HF_TOKEN   = os.getenv("HF_TOKEN")   
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# تسجيل الدخول لو الموديل private
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face ✓")
else:
    raise RuntimeError("HF_TOKEN is not set — required for private model access")

LABEL_MAP = {0: "Clean", 1: "Offensive", 2: "Toxic"}

# action بيحدد إيه اللي يعمله الـ backend
ACTION_MAP = {
    "Clean":     "publish",   # ينشر عادي
    "Offensive": "publish",   # ينشر بس يسجله
    "Toxic":     "delete",    # يمسح من الـ app بس يحفظه في DB
}

# ─────────────────────────────────────────
#  Load Model (عند بداية التطبيق)
# ─────────────────────────────────────────
print(f"Loading model from: {MODEL_NAME}")
tokenizer = XLMRobertaTokenizer.from_pretrained(MODEL_NAME)
model     = XLMRobertaForSequenceClassification.from_pretrained(MODEL_NAME)
model.to(DEVICE)
model.eval()
print(f"Model loaded on {DEVICE}")

# ─────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────
app = FastAPI(
    title="Gym Comment Classifier",
    description="Classifies Arabic/English gym comments into Clean / Offensive / Toxic",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ضيّق ده في Production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────
class ClassifyRequest(BaseModel):
    text: str
    post_id: str | None = None    # اختياري — الـ backend بيبعته لو عايز

class ClassifyResponse(BaseModel):
    text:        str
    post_id:     str | None
    label:       str              # Clean | Offensive | Toxic
    action:      str              # publish | delete
    confidence:  dict             # {"Clean": 0.9, "Offensive": 0.07, "Toxic": 0.03}

# ─────────────────────────────────────────
#  Core Prediction Function
# ─────────────────────────────────────────
def predict(text: str) -> tuple[str, dict]:
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=256,
        padding=True,
    ).to(DEVICE)

    with torch.no_grad():
        logits = model(**inputs).logits
        probs  = torch.softmax(logits, dim=1)[0]
        pred   = torch.argmax(probs).item()

    label      = LABEL_MAP[pred]
    confidence = {LABEL_MAP[i]: round(probs[i].item(), 4) for i in range(3)}
    return label, confidence

# ─────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Gym Comment Classifier is running"}

@app.get("/health")
def health():
    return {"status": "healthy", "device": str(DEVICE)}

@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="text field cannot be empty")

    try:
        label, confidence = predict(req.text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")

    return ClassifyResponse(
        text=req.text,
        post_id=req.post_id,
        label=label,
        action=ACTION_MAP[label],
        confidence=confidence,
    )

# ─────────────────────────────────────────
#  Batch Endpoint (اختياري — لو عندك كتير)
# ─────────────────────────────────────────
class BatchRequest(BaseModel):
    items: list[ClassifyRequest]

class BatchResponse(BaseModel):
    results: list[ClassifyResponse]

@app.post("/classify/batch", response_model=BatchResponse)
def classify_batch(req: BatchRequest):
    if not req.items:
        raise HTTPException(status_code=422, detail="items list cannot be empty")
    if len(req.items) > 50:
        raise HTTPException(status_code=422, detail="Max 50 items per batch")

    results = []
    for item in req.items:
        if not item.text or not item.text.strip():
            continue
        try:
            label, confidence = predict(item.text.strip())
            results.append(ClassifyResponse(
                text=item.text,
                post_id=item.post_id,
                label=label,
                action=ACTION_MAP[label],
                confidence=confidence,
            ))
        except Exception:
            continue

    return BatchResponse(results=results)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)