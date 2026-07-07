# RAG Chatbot

Production-oriented RAG chatbot scaffold for personal documents.

## Current Scope

- FastAPI application factory
- Environment-based configuration
- Health check endpoint
- Base schemas for documents and chat
- Service folders for ingestion, embeddings, vector stores, retrieval, and generation

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

```powershell
uvicorn app.main:app --reload
```

Health check:

```text
GET /api/v1/health
```

## Next Step

Implement text chunking so loaded documents can be split into retrievable chunks before embedding and storing in a vector database.

## Document Loaders

The ingestion layer exposes a single service:

```python
from app.services.ingestion import DocumentLoaderService, LoaderInput

documents = DocumentLoaderService().load(
    LoaderInput(
        source="data/raw/example.pdf",
        title="Optional title",
        user_id="optional-user-id",
    )
)
```

Supported inputs:

- Local text files: `.txt`
- Local markdown files: `.md`
- Local PDF files: `.pdf`
- Local Word files: `.docx`
- HTML pages: `http://...` or `https://...`
- OCR images: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.gif`, `.webp`

Each loader returns a list of `Document` objects with normalized text and metadata:

- `document_id`
- `document_type`
- `source`
- `title`
- `page_number` for PDF pages
- `user_id`
- `mime_type`
- `ingested_at`

### OCR Setup

Image OCR uses `pytesseract`, which is only the Python wrapper. Install the Tesseract OCR executable separately.

On Windows, install Tesseract and set the executable path in `.env` if it is not on `PATH`:

```text
TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
OCR_LANGUAGES="eng"
```

For Vietnamese OCR, install the Vietnamese trained data and use:

```text
OCR_LANGUAGES="eng+vie"
```
