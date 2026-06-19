import json
import os
import torch
from transformers import XLMRobertaTokenizer, XLMRobertaForSequenceClassification


HF_MODEL_REPO = os.getenv("HFMODELREPO", "smaaanwerb/chat_monitoring")
# If running locally with saved model, set this env var to a local path instead
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", None)


class ModelService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.threshold = 0.5        # fallback; overridden by best_threshold.json
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_loaded = False

    def load(self):
        from huggingface_hub import login
        hf_token = os.getenv("HFTOKEN")
        if hf_token:
            login(token=hf_token)

        source = LOCAL_MODEL_PATH if LOCAL_MODEL_PATH else HF_MODEL_REPO
        print(f"Loading model from: {source}")

        self.tokenizer = XLMRobertaTokenizer.from_pretrained(source)
        self.model = XLMRobertaForSequenceClassification.from_pretrained(source)
        self.model.to(self.device)
        self.model.eval()

        # Load best threshold saved during training
        threshold_path = os.path.join(source, "best_threshold.json") if LOCAL_MODEL_PATH else None
        if threshold_path and os.path.exists(threshold_path):
            with open(threshold_path) as f:
                self.threshold = json.load(f)["best_threshold"]
            print(f"Loaded threshold from file: {self.threshold:.4f}")
        else:
            # Try to fetch from HF Hub
            try:
                from huggingface_hub import hf_hub_download
                path = hf_hub_download(repo_id=HF_MODEL_REPO, filename="best_threshold.json")
                with open(path) as f:
                    self.threshold = json.load(f)["best_threshold"]
                print(f"Loaded threshold from HF Hub: {self.threshold:.4f}")
            except Exception as e:
                print(f"Could not load threshold file ({e}), using default: {self.threshold}")

        self.is_loaded = True

    def predict(self, text: str) -> tuple[str, float]:
        """Returns (label, confidence) where label is 'Safe' or 'Warning'."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded yet.")

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            prob_warning = probs[0][1].item()

        label = "Warning" if prob_warning >= self.threshold else "Safe"
        return label, round(prob_warning, 4)
