# RAG Chatbot

Bản ngắn gọn các lệnh chạy chính. Các script chi tiết đã được gom vào `scripts/rag_cli.py`.

## Cài Đặt

```powershell
cd D:\RAG-chatbot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu muốn cài đúng version đã khóa:

```powershell
pip install -r requirements.lock
```

Cài Tesseract OCR:

```powershell
winget install UB-Mannheim.TesseractOCR
tesseract --version
tesseract --list-langs
```

Tạo `.env`:

```powershell
Copy-Item .env.example .env
```

`.env` tối thiểu:

```env
GEMINI_API_KEY=your_key_here
EMBEDDING_LOCAL_FILES_ONLY=true
TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
OCR_LANGUAGES="eng+vie"
CHROMA_PATH=./data/chroma
CHROMA_COLLECTION=personal_docs_bge_m3_1024
```

## Lệnh Chính

Xem toàn bộ CLI:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py --help
```

Preload model:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py preload
```

Kiểm tra đã cache model local:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py preload --local-files-only
```

In chunk và kiểm tra embedding:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py inspect --source Test.pdf --local-files-only
```

Chạy demo mock nhanh:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py demo
```

Chạy demo thật end-to-end:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py demo --real --source Test.pdf --query "Vector Space Model là gì?" --local-files-only
```

Index và chạy evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py eval --index --source Test.pdf --dataset data\evaluation\test_data.jsonl --local-files-only --no-cache
```

Chạy API:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py api --port 8000
```

Chạy test:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py test -q
```

Kiểm tra port:

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py ports --port 8000
```

## API Nhanh

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Upload:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/documents/upload" `
  -F "file=@Test.pdf"
```

Chat:

```powershell
$body = @{
  question = "Vector Space Model là gì?"
  strategy = "parent_child"
  top_k = 3
  fetch_k = 10
  min_score = 0.70
  filters = @{ source_type = "pdf" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body $body
```

## Help Theo Nhóm

```powershell
.\.venv\Scripts\python.exe scripts\rag_cli.py preload --help
.\.venv\Scripts\python.exe scripts\rag_cli.py inspect --help
.\.venv\Scripts\python.exe scripts\rag_cli.py demo --help
.\.venv\Scripts\python.exe scripts\rag_cli.py eval --help
.\.venv\Scripts\python.exe scripts\rag_cli.py api --help
.\.venv\Scripts\python.exe scripts\rag_cli.py test --help
```

