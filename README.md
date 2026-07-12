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

## 4. Kiểm Tra Nhanh

Backend health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 5. Build/Test

```powershell
cd D:\RAG-chatbot
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd D:\RAG-chatbot\frontend
npm run build
```
