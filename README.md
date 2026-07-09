# RAG Chatbot

Hệ thống RAG chatbot cho tài liệu cá nhân, đang được xây từng bước theo hướng production-ready.

Hiện tại project đã có:

- FastAPI API layer cho health, chat, upload và document management.
- Loader cho `PDF`, `DOCX`, `TXT`, `MD`, HTML URL và image OCR.
- OCR bằng Tesseract, hỗ trợ tiếng Việt.
- Chunking pipeline có metadata, content type, section context, parent-child chunks và quality report.
- Retriever layer có dense retrieval và parent-child retrieval baseline.
- RAG answer pipeline với ContextBuilder, PromptBuilder, LLMService và citations.
- Retrieval evaluation baseline với Recall@K, MRR và Citation Accuracy.

## Cài Đặt

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu chưa có `.env`:

```powershell
Copy-Item .env.example .env
```

OCR image cần Tesseract:

```env
TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
OCR_LANGUAGES="eng+vie"
```

Kiểm tra Tesseract:

```powershell
tesseract --list-langs
```

## Chạy API

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/health/ready
```

Chat:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body '{"question":"Bông tuyết Koch được xây dựng như thế nào?","strategy":"parent_child","top_k":3,"min_score":0.78,"filters":{"source_type":"pdf"}}'
```

Upload tài liệu:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/upload" `
  -F "file=@23520108_23520383_23521714.pdf"
```

Các route cũng được mount dưới `/api/v1` để tương thích ngược.

## Chạy Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## In Thử Chunks

In chunks từ PDF mẫu:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\print_chunks.py --limit 3
```

Chạy với file khác:

```powershell
.\.venv\Scripts\python.exe scripts\print_chunks.py path\to\file.pdf --limit 5
```

In thử parent chunks:

```powershell
.\.venv\Scripts\python.exe scripts\print_chunks.py --parents --level parent --limit 2
```

## Đánh Giá Retrieval Baseline

Chạy lexical baseline trên bộ câu hỏi mẫu:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --k 5
```

## Demo Retriever

Chạy nhanh với mock services:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\demo_retriever.py
```

Preload BGE-M3 một lần để cache weight local:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\preload_embedding_model.py
```

Kiểm tra model đã có sẵn trong local cache:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\preload_embedding_model.py --local-files-only
```

Chạy end-to-end với PDF mẫu, BGE-M3 và ChromaDB:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\demo_retriever.py --real --min-score 0.78 --local-files-only
```

## Demo RAG Answer Pipeline

Chạy offline với mock retriever và mock LLM:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\demo_rag.py
```

Chạy thật end-to-end với PDF mẫu, BGE-M3, ChromaDB và Gemini:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe scripts\demo_rag_real.py --provider gemini --min-score 0.78 --local-files-only
```

Các biến `.env` chính cho LLM provider:

```env
GEMINI_API_KEY=
OPENROUTER_API_KEY=
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="qwen3:8b"
```

## Cấu Trúc Chính

```text
app/
  api/
  core/
  schemas/
  services/
    ingestion/
    chunking/
    evaluation/
    llm/
    rag/
    retrieval/
scripts/
tests/
data/
```

## Bước Tiếp Theo

Xây dựng embedding pipeline và ChromaDB local vector store từ output `DocumentChunk`.
