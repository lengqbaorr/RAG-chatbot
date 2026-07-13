# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    TESSERACT_CMD=/usr/bin/tesseract \
    OCR_LANGUAGES=eng+vie \
    HF_HOME=/app/data/hf_cache \
    TRANSFORMERS_CACHE=/app/data/hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/data/hf_cache/sentence-transformers

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgl1 \
        libglib2.0-0 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip --retries 10 --timeout 120 \
    && pip install -r requirements.txt --retries 10 --timeout 120

COPY app ./app

RUN mkdir -p /app/data/raw /app/data/chroma /app/data/hf_cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
