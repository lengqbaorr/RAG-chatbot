# RAG Chatbot

Ứng dụng RAG cá nhân gồm FastAPI backend và React frontend.

Hỗ trợ upload và hỏi đáp trên PDF, DOCX, TXT, Markdown, URL/HTML và ảnh OCR.

## Yêu Cầu

- Python 3.11
- Node.js 20+
- Tesseract OCR
- Gemini API key
- Docker Desktop nếu chạy bằng Docker

## Cài Local

```powershell
cd D:\RAG-chatbot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Cập nhật `.env`:

```env
GEMINI_API_KEY=your_key_here
TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
OCR_LANGUAGES="eng+vie"
DEFAULT_MIN_SCORE=0.76
AUTH_ENABLED=false
```

Cài frontend:

```powershell
cd D:\RAG-chatbot\frontend
npm install
Copy-Item .env.example .env
```

`frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AUTH_MODE=disabled
```

## Chạy Local

Terminal 1:

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd D:\RAG-chatbot\frontend
npm run dev
```

Mở:

```text
http://127.0.0.1:5173
```

## Chạy Docker

```powershell
cd D:\RAG-chatbot
Copy-Item deploy\docker.env.example deploy\docker.env
```

Cập nhật `deploy/docker.env`:

```env
GEMINI_API_KEY=your_key_here
DEFAULT_MIN_SCORE=0.76
```

Chạy:

```powershell
docker compose build
docker compose up -d
```

Mở:

```text
http://127.0.0.1:8080
```

Lệnh hữu ích:

```powershell
docker compose ps
docker compose logs -f backend
docker compose down
```

## Kiểm Tra

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Test Và Build

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd D:\RAG-chatbot\frontend
npm run build
```

## Benchmark Retrieval

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m app.cli.benchmark --dataset benchmarks\sample_retrieval.jsonl --strategies parent_child,dense --top-k 3 --fetch-k 8 --min-score 0.76 --page-tolerance 1 --auto-source-filter --local-files-only --show-failures
```

## Benchmark End-to-End RAG

Chạy thử 5 câu:

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m app.cli.rag_benchmark --dataset benchmarks\sample_retrieval.jsonl --strategies parent_child --top-k 3 --fetch-k 8 --min-score 0.76 --auto-source-filter --temperature 0 --max-tokens 2048 --request-delay-seconds 13 --offset 0 --limit 5 --local-files-only --show-failures
```

Chạy batch 10 câu tiếp theo:

```powershell
.\.venv\Scripts\python.exe -m app.cli.rag_benchmark --dataset benchmarks\sample_retrieval.jsonl --strategies parent_child --top-k 3 --fetch-k 8 --min-score 0.76 --auto-source-filter --temperature 0 --max-tokens 2048 --request-delay-seconds 13 --offset 10 --limit 10 --local-files-only --show-failures
```

Gemini free tier giới hạn request/phút. Nếu gặp `429`, tăng `--request-delay-seconds` lên `15` hoặc `20`.

## Deploy Demo Bằng Cloudflare Tunnel

Sau khi Docker đang chạy:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Copy URL `trycloudflare.com` để demo.

## CI/CD

Workflow chính:

```text
.github/workflows/ci.yml
.github/workflows/deploy-windows-runner.yml
```

Deploy Windows dùng GitHub self-hosted runner và Docker Compose. Secret cần có:

```text
DOCKER_ENV
```

`DOCKER_ENV` là nội dung của `deploy/docker.env`.
