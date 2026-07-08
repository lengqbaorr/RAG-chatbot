# RAG Chatbot

Hệ thống RAG chatbot cho tài liệu cá nhân, đang được xây từng bước theo hướng production-ready.

Hiện tại project đã có:

- FastAPI app skeleton.
- Loader cho `PDF`, `DOCX`, `TXT`, `MD`, HTML URL và image OCR.
- OCR bằng Tesseract, hỗ trợ tiếng Việt.
- Chunking pipeline có metadata, content type, section context, parent-child chunks và quality report.
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
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```

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
scripts/
tests/
data/
```

## Bước Tiếp Theo

Xây dựng embedding pipeline và ChromaDB local vector store từ output `DocumentChunk`.
