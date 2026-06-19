FROM python:3.10-slim

# ── System deps ──────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ──────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ─────────────────────────────
COPY app.py .

# Hugging Face Spaces يشتغل على port 7860
EXPOSE 7860

# ── Run ──────────────────────────────────
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
