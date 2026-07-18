# RAG Chatbot

FastAPI backend + React frontend cho hệ thống RAG cá nhân.

Input hỗ trợ: PDF, DOCX, TXT, Markdown, URL/HTML và ảnh OCR (`png`, `jpg`, `jpeg`, `bmp`, `gif`, `tif`, `tiff`, `webp`).

## 1. Cài Backend

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
LLM_MAX_TOKENS=2048
TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
OCR_LANGUAGES="eng+vie"
AUTH_ENABLED=false
```

Nếu muốn bật đăng nhập local:

```env
AUTH_ENABLED=true
AUTH_LOCAL_USERNAME=local
AUTH_LOCAL_PASSWORD=your_password
AUTH_SECRET_KEY=your_long_random_secret
```

Reranker mặc định tắt. Khi bật trong Settings lần đầu, model cross-encoder có thể cần tải từ Hugging Face:

```env
RERANKER_ENABLED=false
RERANKER_MODEL="BAAI/bge-reranker-v2-m3"
```

Retrieval fallback giúp tự thử lại với ngưỡng thấp hơn nếu lần đầu không tìm thấy context:

```env
DEFAULT_MIN_SCORE=0.76
RETRIEVAL_FALLBACK_ENABLED=true
RETRIEVAL_FALLBACK_MIN_SCORE=0.55
```

Tải trước reranker nếu không muốn request chat đầu tiên bị treo lâu:

```powershell
.\.venv\Scripts\python.exe -m app.cli.preload_reranker --clean-incomplete
```

Cài Tesseract nếu chưa có:

```powershell
winget install UB-Mannheim.TesseractOCR
```

## 2. Cài Frontend

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

## 3. Chạy Chương Trình

Terminal 1, chạy backend:

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, chạy frontend:

```powershell
cd D:\RAG-chatbot\frontend
npm run dev
```

Mở trình duyệt:

```text
http://127.0.0.1:5173
```

## 4. Chạy Bằng Docker Compose

Yêu cầu:

- Docker Desktop
- Gemini API key

Tạo env Docker:

```powershell
cd D:\RAG-chatbot
Copy-Item deploy\docker.env.example deploy\docker.env
```

Cập nhật trong `deploy/docker.env`:

```env
GEMINI_API_KEY=your_key_here
```

Build và chạy:

```powershell
docker compose build
docker compose up -d
```

Mở frontend:

```text
http://127.0.0.1:8080
```

Backend health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Xem log:

```powershell
docker compose logs -f backend
```

Dừng:

```powershell
docker compose down
```

Xóa cả dữ liệu Docker volume:

```powershell
docker compose down -v
```

Lưu ý: Docker phase hiện tại dùng SQLite + ChromaDB embedded trong volume `rag_data`. PostgreSQL sẽ là phase tiếp theo.

## 5. Kiểm Tra Nhanh

Backend health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 6. Build/Test

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd D:\RAG-chatbot\frontend
npm run build
```

## 7. Benchmark Retrieval

Tạo dataset JSONL theo mẫu:

```text
benchmarks/sample_retrieval.jsonl
```

Chạy benchmark Dense và Parent-child trên vector store hiện tại:

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m app.cli.benchmark `
  --dataset benchmarks\sample_retrieval.jsonl `
  --strategies parent_child,dense `
  --top-k 3 `
  --fetch-k 8 `
  --min-score 0.76 `
  --page-tolerance 1 `
  --auto-source-filter `
  --local-files-only `
  --show-failures
```

Xuất report:

```powershell
.\.venv\Scripts\python.exe -m app.cli.benchmark `
  --dataset benchmarks\sample_retrieval.jsonl `
  --page-tolerance 1 `
  --auto-source-filter `
  --output-json data\benchmark\retrieval_report.json `
  --output-md data\benchmark\retrieval_report.md `
  --local-files-only
```

Metrics chính:

- `recall@1/3/5/10`
- `mrr`
- `precision@k`
- `citation`
- `keywords`
- `unanswerable`
- `avg_latency`

## 8. Benchmark End-to-End RAG

Benchmark này chạy đầy đủ retrieval, context builder, Gemini và answer evaluation. Lệnh này tốn quota LLM, nên chạy thử `--limit` trước:

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m app.cli.rag_benchmark `
  --dataset benchmarks\sample_retrieval.jsonl `
  --strategies parent_child `
  --top-k 3 `
  --fetch-k 8 `
  --min-score 0.76 `
  --auto-source-filter `
  --temperature 0 `
  --max-tokens 2048 `
  --request-delay-seconds 13 `
  --offset 0 `
  --limit 5 `
  --local-files-only `
  --show-failures
```

Chạy theo batch 10 câu:

```powershell
.\.venv\Scripts\python.exe -m app.cli.rag_benchmark `
  --dataset benchmarks\sample_retrieval.jsonl `
  --strategies parent_child `
  --top-k 3 `
  --fetch-k 8 `
  --min-score 0.76 `
  --auto-source-filter `
  --temperature 0 `
  --max-tokens 2048 `
  --request-delay-seconds 13 `
  --offset 10 `
  --limit 10 `
  --local-files-only `
  --show-failures
```

Chạy toàn bộ dataset và xuất report:

```powershell
.\.venv\Scripts\python.exe -m app.cli.rag_benchmark `
  --dataset benchmarks\sample_retrieval.jsonl `
  --strategies parent_child `
  --top-k 3 `
  --fetch-k 8 `
  --min-score 0.76 `
  --auto-source-filter `
  --temperature 0 `
  --max-tokens 2048 `
  --request-delay-seconds 13 `
  --output-json data\benchmark\rag_report.json `
  --output-md data\benchmark\rag_report.md `
  --local-files-only `
  --show-failures
```

Với Gemini free tier 5 requests/phút, 100 câu sẽ mất khoảng 22 phút trở lên. Nếu gặp 429, đợi khoảng 1 phút rồi chạy lại với `--request-delay-seconds 15`.

Metrics chính:

- `answer_acc`
- `answer_keywords`
- `citation`
- `source_hit`
- `unanswerable`
- `retrieval_latency`
- `llm_latency`
- `total_latency`

## 9. CI/CD + Deploy

CI đã có tại:

```text
.github/workflows/ci.yml
```

CI chạy:

- Backend tests
- Frontend build
- Docker build backend/frontend

Deploy khuyến nghị cho máy Windows đang chạy Docker Desktop:

```text
.github/workflows/deploy-windows-runner.yml
```

Workflow này chạy trên GitHub Actions self-hosted runner đặt trên chính máy Windows deploy. Nó sẽ:

- Checkout code mới.
- Ghi `deploy/docker.env` từ GitHub Secret.
- `docker compose build`.
- `docker compose up -d`.
- Kiểm tra `/health/ready`.

GitHub Secret cần tạo:

```text
DOCKER_ENV
```

Giá trị của `DOCKER_ENV` là toàn bộ nội dung file `deploy/docker.env`, bao gồm `GEMINI_API_KEY`.

Runner labels cần có:

```text
self-hosted
Windows
rag-chatbot
```

Sau khi cấu hình runner, deploy bằng:

```text
GitHub → Actions → Deploy Windows Docker Compose → Run workflow
```

Hoặc push vào `main/master`, workflow sẽ tự deploy.

Deploy qua SSH/server nằm ở:

```text
.github/workflows/deploy-compose.yml
```

Cần cấu hình GitHub Secrets nếu dùng SSH deploy:

```text
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
DEPLOY_PORT
DEPLOY_PATH
```
