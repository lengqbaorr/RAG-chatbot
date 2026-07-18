# RAG Chatbot Architecture

Tai lieu nay mo ta kien truc codebase hien tai cua RAG Chatbot. Noi dung duoc viet theo trang thai da implement, khong tron lan voi roadmap. Nhung muc roadmap duoc tach rieng o cuoi file.

## 1. Product Scope

RAG Chatbot la ung dung hoi dap tai lieu ca nhan gom:

- FastAPI backend.
- React/Vite frontend.
- Document upload va indexing.
- Loader da dinh dang.
- Chunking + parent-child chunking.
- BGE-M3 embedding.
- SQLite embedding cache.
- ChromaDB vector store.
- Retriever + optional reranker.
- Gemini LLM provider.
- Streaming chat bang Server-Sent Events.
- Persistent chat history.
- Document/source preview.
- Docker Compose deploy local/private.
- GitHub Actions CI/CD qua self-hosted Windows runner.

He thong hien tai phu hop cho local/private deployment va demo qua Cloudflare Tunnel. No chua phai SaaS multi-user cloud-native hoan chinh.

## 2. High-Level Runtime

```text
Browser
  |
  v
React Frontend
  |
  | HTTP / SSE
  v
FastAPI Backend
  |
  +-- Auth / Settings / Health APIs
  +-- Document APIs
  +-- Job APIs
  +-- Chat APIs
  |
  v
Service Layer
  |
  +-- Loader
  +-- Chunker
  +-- Embedding
  +-- VectorStore
  +-- Retriever
  +-- RAG Pipeline
  +-- LLM Provider
  |
  v
Local Persistence
  |
  +-- SQLite metadata DB
  +-- SQLite embedding cache
  +-- ChromaDB embedded data
  +-- Local raw files
```

Docker deployment:

```text
Browser
  |
  v
frontend container: Nginx + React static build
  |
  | /api/v1 proxied by Nginx
  v
backend container: FastAPI/Uvicorn
  |
  v
Docker volume: rag_data
  |
  +-- /app/data/metadata.db
  +-- /app/data/embeddings.db
  +-- /app/data/chroma
  +-- /app/data/raw
  +-- /app/data/hf_cache
```

Public demo:

```text
Internet user
  |
  v
Cloudflare Tunnel quick URL
  |
  v
http://127.0.0.1:8080 on local Windows machine
  |
  v
Docker Compose frontend/backend
```

## 3. Repository Layout

Important paths:

```text
app/
  api/                  FastAPI routes, schemas, dependencies
  core/                 config, startup, logging, exception mapping
  db/                   SQLite database wrapper and migrations
  services/             business logic
  main.py               ASGI entrypoint

frontend/
  src/                  React application
  Dockerfile            production frontend image
  nginx.conf            static serving + API proxy

deploy/
  docker.env.example    Docker env template, no secrets

.github/workflows/
  ci.yml
  deploy-windows-runner.yml
  deploy-compose.yml

Dockerfile              backend image
docker-compose.yml      local/private deploy stack
DEPLOYMENT.md           deployment guide
README.md               runbook
```

## 4. Backend Entry Points

Main entry:

- `app/main.py`
- `app/api/main.py`

FastAPI registers all routes both at root and `/api/v1`.

Main endpoints:

- `GET /health`
- `GET /health/ready`
- `GET /auth/status`
- `POST /auth/login`
- `GET /auth/me`
- `POST /documents/upload`
- `POST /documents/url`
- `GET /documents`
- `GET /documents/{source_id}`
- `GET /documents/{source_id}/preview`
- `GET /documents/{source_id}/chunks/{chunk_id}`
- `GET /documents/{source_id}/file`
- `DELETE /documents/{source_id}`
- `POST /documents/reindex/{source_id}`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /chat`
- `POST /chat/stream`
- `POST /chat/sessions`
- `GET /chat/sessions`
- `GET /chat/sessions/{session_id}`
- `GET /chat/sessions/{session_id}/messages`
- `PATCH /chat/sessions/{session_id}`
- `DELETE /chat/sessions/{session_id}`
- `GET /settings`
- `PATCH /settings`
- `POST /settings/reset`

Runtime CLI:

- `python -m app.cli.preload_reranker --clean-incomplete`

## 5. Core Layer

Location:

- `app/core/config.py`
- `app/core/startup.py`
- `app/core/logging.py`
- `app/core/exceptions.py`

Responsibilities:

- Load `.env` for local Python runtime.
- Initialize service singletons during FastAPI lifespan.
- Configure CORS.
- Install request logging middleware.
- Map domain exceptions to stable HTTP errors.
- Stop background indexing worker during shutdown.

`build_services()` in `app/core/startup.py` wires the runtime graph:

```text
Database
  -> repositories
  -> services
  -> loader/chunker/embedding/vectorstore
  -> retriever
  -> RAG pipeline
  -> FastAPI app.state
```

FastAPI routes retrieve services from `app.state` through `app/api/dependencies.py`.

## 6. Configuration

Local dev reads:

- `.env`

Docker Compose reads:

- `deploy/docker.env`

Templates:

- `.env.example`
- `deploy/docker.env.example`

Important environment variables:

```text
GEMINI_API_KEY
CHROMA_PATH
CHROMA_COLLECTION
METADATA_DB_PATH
EMBEDDING_CACHE_PATH
UPLOAD_DIR
EMBEDDING_MODEL
EMBEDDING_DIMENSION
EMBEDDING_LOCAL_FILES_ONLY
LLM_MODEL
LLM_MAX_TOKENS
DEFAULT_TOP_K
DEFAULT_FETCH_K
DEFAULT_MIN_SCORE
RETRIEVAL_FALLBACK_ENABLED
RERANKER_ENABLED
RERANKER_MODEL
AUTH_ENABLED
AUTH_LOCAL_USERNAME
AUTH_LOCAL_PASSWORD
AUTH_SECRET_KEY
```

Security:

- `.env` is ignored.
- `deploy/docker.env` is ignored.
- `deploy/docker.env.example` is committed and must not contain secrets.
- GitHub Actions deploy writes `deploy/docker.env` from secret `DOCKER_ENV`.

## 7. Database and Metadata Store

Location:

- `app/db/database.py`
- `app/db/migrations/001_initial.sql`
- `app/services/document/repository.py`
- `app/services/jobs/repository.py`
- `app/services/chat_history/repository.py`
- `app/services/settings/repository.py`

Current implementation:

- SQLite.
- One local metadata DB file.
- Lightweight compatible migrations are applied by initializer.

Main tables:

- `documents`
- `chunks`
- `index_jobs`
- `chat_sessions`
- `chat_messages`
- `user_settings`

SQLite stores product/business metadata:

- document lifecycle
- chunk metadata and preview content
- indexing jobs
- chat history
- selected sources
- runtime settings

SQLite does not store vector embeddings except the separate embedding cache DB.

Current limitation:

- Repository layer is SQLite-specific.
- PostgreSQL/Supabase requires repository/database migration work.

## 8. Document Management

Location:

- `app/services/document`
- `app/api/routes/documents.py`

Main classes:

- `DocumentRepository`
- `DocumentService`
- `DocumentRecord`
- `ChunkRecord`
- `DocumentPreview`
- `DocumentChunkPreview`

Document lifecycle:

```text
PENDING -> RUNNING -> COMPLETED
                   -> FAILED
COMPLETED -> DELETED
```

`documents` stores:

- `source_id`
- `source_name`
- `original_filename`
- `mime_type`
- `file_size`
- `sha256`
- `raw_path`
- `upload_time`
- `status`
- `owner`
- `language`
- `page_count`
- `chunk_count`
- `embedding_model`
- `embedding_dimension`
- `collection_name`
- `deleted_at`

`chunks` stores:

- `chunk_id`
- `source_id`
- `parent_id`
- `content`
- `page_start`
- `page_end`
- `section_title`
- `header_path`
- `token_count`
- `retrieval_excluded`
- `content_hash`

Important boundary:

- ChromaDB is not the document lifecycle source of truth.
- SQLite document metadata is the product source of truth.

## 9. Ingestion and Loader Layer

Location:

- `app/services/ingestion`

Supported inputs:

- PDF
- DOCX
- TXT
- Markdown
- URL/HTML
- Direct PDF URL
- Image OCR

OCR:

- Tesseract.
- Docker image installs `tesseract-ocr-eng` and `tesseract-ocr-vie`.
- Local Windows uses `TESSERACT_CMD`.

Loader responsibility:

- Load raw source.
- Extract normalized text.
- Preserve source metadata.
- Return internal document objects.

Loader does not:

- chunk
- embed
- write vector DB
- call LLM

## 10. Chunking Pipeline

Location:

- `app/services/chunking`

Main components:

- `normalizers.py`
- `parsers.py`
- `splitters.py`
- `postprocessors.py`
- `reports.py`
- `validators.py`
- `pipeline.py`

Responsibilities:

- Normalize text.
- Parse page/line/heading structure.
- Detect content type.
- Split into child chunks.
- Build parent chunks.
- Merge small chunks.
- Add section context to embedding text.
- Validate token budget.
- Produce quality metadata.

Current runtime config in `startup.py`:

```text
chunk_size_tokens=450
chunk_overlap_tokens=60
build_parent_chunks=True
```

Content types:

- `body`
- `cover`
- `toc`
- `reference`
- `table`
- `code`

Retrieval-excluded chunks are skipped by embedding service through:

```text
skip_retrieval_excluded=True
```

## 11. Indexing Platform

Location:

- `app/services/indexing`
- `app/services/jobs`

Main classes:

- `IndexingService`
- `IndexingPipeline`
- `InMemoryIndexingQueue`
- `ThreadedIndexingWorker`
- `JobService`
- `JobRepository`

Flow:

```text
POST /documents/upload or /documents/url
  |
  v
Validate input
  |
  v
Save raw file or URL locator
  |
  v
Create document record
  |
  v
Create index job
  |
  v
Queue task
  |
  v
ThreadedIndexingWorker
  |
  +-- Loading
  +-- Chunking
  +-- Embedding
  +-- VectorStore upsert
  +-- Save chunk metadata
  +-- Mark completed/failed
```

Job statuses:

- `PENDING`
- `RUNNING`
- `FAILED`
- `COMPLETED`
- `CANCELLED`

Job stages:

- `Uploading`
- `Loading`
- `Chunking`
- `Embedding`
- `VectorStore`
- `Finishing`

Current limitation:

- Worker is an in-process local thread.
- It is not Celery/RQ/Redis yet.
- If backend process stops, in-memory queue is lost.

## 12. Embedding Layer

Location:

- `app/services/embedding`

Main provider:

- `BGEM3EmbeddingProvider`

Runtime model:

- default `BAAI/bge-m3`
- default dimension `1024`

Responsibilities:

- Build embedding text.
- Embed chunks.
- Embed queries.
- Batch embedding.
- Validate dimensions.
- Cache embeddings in SQLite.
- Hide provider-specific details.

Cache:

- `SQLiteEmbeddingCache`
- DB path from `EMBEDDING_CACHE_PATH`
- avoids re-embedding same content/model hash.

Docker:

- Hugging Face cache stored in `/app/data/hf_cache`.
- Persisted by Docker volume `rag_data`.
- Do not run `docker compose down -v` unless you intentionally want to delete model/data cache.

Current performance note:

- BGE-M3 on CPU is slow for first load and large indexing jobs.
- First Docker run may download model from Hugging Face.

## 13. VectorStore Layer

Location:

- `app/services/vectorstore`

Current implementation:

- `ChromaVectorStore`
- embedded/local ChromaDB

Responsibilities:

- Upsert embedded chunks.
- Similarity search.
- Delete by `source_id`.
- Fetch by chunk ID.
- Apply neutral metadata filters.

Chroma stores:

- vectors
- retrieval metadata
- text needed by retrieval and fallback preview

Chroma does not store:

- document lifecycle
- index job state
- chat sessions
- user settings

Current limitation:

- Qdrant/Pinecone provider is not implemented yet.

## 14. Retrieval Layer

Location:

- `app/services/retrieval`

Main strategies:

- `DenseRetriever`
- `ParentChildRetriever`

Pipeline:

```text
RetrievalQuery
  |
  v
QueryPreprocessor
  |
  v
EmbeddingService.embed_query
  |
  v
BaseVectorStore.similarity_search
  |
  v
ScoreThresholdFilter
  |
  v
ContentTypeFilter
  |
  v
Deduplicator
  |
  v
ContextSelector
  |
  v
RetrievalResult
```

Retriever depends on:

- `EmbeddingService`
- `BaseVectorStore`

Retriever does not call:

- LLM
- PromptBuilder
- FastAPI
- Chroma SDK directly

Default runtime values:

```text
DEFAULT_RETRIEVAL_STRATEGY=parent_child
DEFAULT_TOP_K=3
DEFAULT_FETCH_K=8
DEFAULT_MIN_SCORE=0.76
RETRIEVAL_FALLBACK_ENABLED=true
RETRIEVAL_FALLBACK_MIN_SCORE=0.55
```

## 15. Reranking and Evaluation

Location:

- `app/services/reranking`
- `app/services/evaluation`

Reranking:

- Optional.
- Disabled by default.
- Uses cross-encoder reranker when enabled.
- Default model: `BAAI/bge-reranker-v2-m3`.
- Reranker keeps original retrieval score.
- Reranker score is fused conservatively:

```text
fused_score = original_retrieval_score * 0.65 + normalized_rerank_score * 0.35
```

Fallback:

- If reranker fails, RAGPipeline falls back to original retrieval result.

Evaluation:

- Local deterministic retrieval benchmark framework.
- Computes Recall@K, Precision@K, MRR, citation accuracy, keyword coverage.
- Baseline does not use LLM-as-judge.
- CLI entrypoint:

```powershell
python -m app.cli.benchmark --dataset benchmarks\sample_retrieval.jsonl
```

Benchmark dataset formats:

- JSONL: one case per line.
- JSON: list of cases or object with `cases`.

Benchmark case fields:

- `id`
- `question`
- `expected_source_name`
- `expected_pages`
- `expected_section`
- `expected_keywords`
- `answerable`
- `group`

## 16. Conversation Context Layer

Location:

- `app/services/conversation`
- `app/services/chat_history`
- `app/api/routes/chat.py`

Purpose:

- Support follow-up questions.
- Keep original user question unchanged for answer generation.
- Build a separate retrieval query enriched by recent conversation.
- Pass recent user/assistant messages into PromptBuilder.

Flow:

```text
User question
  |
  v
ChatHistoryService saves user message
  |
  v
ConversationContextService reads recent completed messages
  |
  +-- standalone question -> retrieval_query = original question
  |
  +-- follow-up question -> retrieval_query = previous anchor + current question
  |
  v
RAGPipeline retrieves with retrieval_query
  |
  v
PromptBuilder receives original question + chat history + context
```

Report fields:

- `original_question`
- `retrieval_query`
- `query_rewritten`
- `used_history_messages`

Current limitation:

- Rewrite is rule-based and deterministic.
- It is not a full LLM-based query rewriting system.

## 17. RAG Answer Pipeline

Location:

- `app/services/rag`
- `app/services/llm`

Pipeline:

```text
Original question
  |
  v
ConversationContextService
  |
  v
RetrieverService using retrieval_query
  |
  v
optional Reranker
  |
  v
ContextBuilder
  |
  v
PromptBuilder
  |
  v
LLMService
  |
  v
CitationBuilder
  |
  v
RAGAnswer
```

LLM providers:

- `GeminiProvider`
- `OpenRouterProvider`
- `OllamaProvider`

Current product provider:

- Gemini

Important boundaries:

- PromptBuilder does not call LLM.
- LLMProvider does not know retriever/vector store.
- Retriever does not call LLM.
- RAGPipeline orchestrates; it does not contain provider-specific details.

Answer output:

- inline `[Source n]` markers are stripped from final answer text.
- sources are returned as structured citation objects and shown separately in UI.

## 18. Streaming Chat

Endpoint:

- `POST /chat/stream`

Transport:

- Server-Sent Events

Events:

- `start`
- `delta`
- `complete`
- `error`

Frontend behavior:

- consumes SSE stream.
- renders generated text with typewriter-style perceived realtime.
- supports cancel via AbortController.
- final event carries answer, sources, report and session ID.

Backend behavior:

- streams LLM provider chunks.
- filters inline source markers.
- saves completed/cancelled/failed assistant messages to chat history.

## 19. Authentication

Location:

- `app/services/auth`
- `app/api/routes/auth.py`
- `frontend/src/store/authStore.ts`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/layout/AuthGate.tsx`

Current auth:

- Single local username/password.
- Optional.
- Backend controlled by `AUTH_ENABLED`.
- Frontend controlled by `VITE_AUTH_MODE`.
- Docker Compose currently builds frontend with:

```text
VITE_AUTH_MODE=server
```

Public endpoints:

- `/health`
- `/health/ready`
- `/auth/status`
- `/auth/login`

Protected endpoints when auth is enabled:

- documents
- jobs
- chat
- chat sessions
- settings

Token:

- HMAC-signed bearer token.
- Stored in frontend local storage.
- Sent as `Authorization: Bearer ...`.

Current limitation:

- No OAuth.
- No multi-user account model yet.
- `owner` fields exist as preparation for future multi-tenancy.

## 20. Chat History

Location:

- `app/services/chat_history`
- `app/api/routes/chat_sessions.py`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/chat/ChatWindow.tsx`

Backend stores:

- sessions
- user messages
- assistant messages
- selected documents
- citation sources
- message status
- timestamps

Message statuses:

- `completed`
- `cancelled`
- `failed`

Frontend supports:

- new chat
- load chat sessions
- rename session
- delete session
- restore selected sources
- persist conversations after browser refresh

## 21. Settings Persistence

Location:

- `app/services/settings`
- `app/api/routes/settings.py`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/store/settingsStore.ts`

Flow:

```text
Frontend Settings UI
  |
  v
PATCH /settings
  |
  v
SettingsService
  |
  v
SQLite user_settings
```

Persisted runtime settings:

- retrieval strategy
- top K
- fetch K
- min score
- reranker enabled
- reranker model
- LLM model
- temperature
- max tokens

Settings service merges:

- `.env` or Docker env defaults
- SQLite user overrides

## 22. Frontend Architecture

Location:

- `frontend/src/api`
- `frontend/src/hooks`
- `frontend/src/store`
- `frontend/src/components`
- `frontend/src/pages`
- `frontend/src/types`

Stack:

- React
- TypeScript
- Vite
- TailwindCSS
- TanStack Query
- Zustand
- React Router
- Framer Motion
- React Markdown

Frontend responsibilities:

- API client wraps backend endpoints.
- TanStack Query handles server state.
- Zustand handles local UI/client state.
- Components are feature-oriented and reusable.

Main screens:

- Dashboard
- Documents
- Jobs
- Chat
- Settings
- Login

Frontend production:

- built by `frontend/Dockerfile`.
- served by Nginx.
- API calls go to `/api/v1`.
- `frontend/nginx.conf` proxies `/api/` to backend container.

## 23. Source Selection, Citations, Preview

Source selection:

- Source panel lists uploaded/completed documents.
- Tick means include document.
- Untick means exclude only that document.
- Toggling one source does not auto-toggle others.

Chat request sends:

- `selected_source_ids`
- neutral `filters.source_id`

Backend intersects selected IDs with completed documents, so failed/running/deleted documents are not retrieved.

Citation payload:

- `source_id`
- `source_name`
- `page_start`
- `page_end`
- `section_title`
- `chunk_id`
- `score`
- `content_preview`

UI behavior:

- Shows only the best source for latest answer, selected by highest score.
- Does not display raw retrieved text as separate citation block.
- Clicking source opens document preview.
- PDF preview opens page via browser PDF viewer `#page=N`.
- Text-like preview uses stored chunk text.

Current limitation:

- PDF exact highlight coordinates are not stored yet.

## 24. Health and Observability

Location:

- `app/services/health.py`
- `app/api/routes/health.py`

Health reports:

- app status
- database status
- embedding service status
- embedding model name
- embedding model loaded/cached flags
- vector store status
- LLM provider
- reranker model name
- reranker loaded/cached flags
- upload directory
- free disk space
- Chroma collection
- collection count
- pending jobs
- ready flag

Logging:

- request latency
- request ID
- endpoint
- source ID/job ID where available
- retrieval strategy
- number of sources
- stack traces on errors

Secrets and full document content should not be logged.

## 25. Docker Deployment

Files:

- `Dockerfile`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `docker-compose.yml`
- `deploy/docker.env.example`
- `deploy/docker.env` local only

Backend image:

- base `python:3.11-slim`
- installs Tesseract and language data
- installs Python dependencies with retry/timeout and BuildKit pip cache
- exposes port `8000`
- starts Uvicorn

Frontend image:

- builds React with Node 22
- serves `dist` with Nginx
- proxies `/api/` to backend
- exposes port `80`

Compose services:

- `backend`
- `frontend`

Compose ports:

- backend: `8000:8000`
- frontend: `8080:80`

Compose volume:

- `rag_data:/app/data`

Persisted in `rag_data`:

- metadata DB
- embedding cache DB
- Chroma data
- raw uploads
- Hugging Face model cache

Normal local Docker commands:

```powershell
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend
```

Do not run this unless intentionally deleting all local Docker data/model cache:

```powershell
docker compose down -v
```

## 26. CI/CD

Files:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-windows-runner.yml`
- `.github/workflows/deploy-compose.yml`
- `DEPLOYMENT.md`

CI workflow:

```text
push / pull_request
  |
  +-- backend tests on GitHub-hosted Ubuntu
  +-- frontend build on GitHub-hosted Ubuntu
  +-- Docker image build test
```

Windows deploy workflow:

```text
push main/master or manual trigger
  |
  v
GitHub Actions
  |
  v
self-hosted Windows runner
  |
  v
write deploy/docker.env from GitHub secret DOCKER_ENV
  |
  v
docker compose build
  |
  v
docker compose up -d
  |
  v
check http://127.0.0.1:8000/health/ready
```

Current deploy runner:

- runs on `[self-hosted, Windows]`
- concurrency group: `windows-docker-compose-deploy`
- `cancel-in-progress: true`

Important:

- GitHub Actions deploy updates the app on the Windows machine.
- It does not create public hosting by itself.
- Public access currently requires Cloudflare Tunnel or another public server/cloud.

Optional SSH deploy workflow:

- `.github/workflows/deploy-compose.yml`
- prepared for a Docker Compose server reachable by SSH.

## 27. Cloudflare Tunnel Demo

Current public demo approach:

```text
Docker Compose app on local Windows
  |
  v
cloudflared quick tunnel
  |
  v
trycloudflare.com public URL
```

Quick tunnel command:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Properties:

- free
- fast to demo
- URL changes each run
- terminal must stay open
- Windows machine must stay on
- Docker Desktop must stay running

Named tunnel with custom domain:

- possible with Cloudflare account and domain using Cloudflare DNS.
- gives stable URL.
- can run as Windows Service.
- still requires local Windows machine to remain online unless backend is moved to cloud.

## 28. Current Production Boundaries

Production-ready baseline already implemented:

- Document metadata is separate from vector DB.
- Upload/indexing has job lifecycle.
- Chat uses SSE streaming.
- Chat history is persistent.
- Runtime settings are persisted.
- Source selection is explicit.
- Citation preview is structured.
- Best-source navigation is supported.
- Retrieval fallback reduces false no-context answers.
- Conversation context supports simple follow-up questions.
- Docker Compose deployment works.
- GitHub Actions self-hosted deploy works.

Known limitations:

- SQLite is local/single-user oriented.
- ChromaDB is embedded/local.
- Raw file storage is local disk.
- Background worker is an in-process thread.
- Public demo depends on local machine being online.
- Auth is local single-user, not OAuth/multi-user.
- Reranker is optional and disabled by default due CPU latency.
- BGE-M3 CPU embedding is slow for large indexing jobs.
- PDF preview does not have coordinate-level highlighting.
- Model download progress is not streamed to UI.

## 29. Cloud-Native Migration Roadmap

Target cloud architecture under consideration:

```text
Frontend:    Cloudflare Pages
Backend:     Hugging Face Spaces or another container host
Vector DB:   Qdrant Cloud
Metadata:    Supabase PostgreSQL
Raw files:   Supabase Storage
LLM:         Gemini
```

This is not implemented yet. Required code changes:

1. Add `QdrantVectorStore`.
   - Implement provider under `app/services/vectorstore/providers`.
   - Add `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`.
   - Keep `BaseVectorStore` contract stable.

2. Add PostgreSQL metadata repository.
   - Current repositories are SQLite-specific.
   - Add SQLAlchemy/psycopg or separate Postgres repository implementation.
   - Add migration tool such as Alembic.

3. Add object storage provider.
   - Replace local `raw_path` file assumption with storage locator.
   - Add Supabase Storage/S3-compatible provider.
   - Update document preview/download to read from storage provider.

4. Split worker from API process.
   - Replace in-memory queue with external queue.
   - Candidate: Redis/RQ, Celery, Dramatiq.

5. Build and push Docker images from CI.
   - Current deploy builds images on the Windows machine.
   - Better production flow:

```text
CI builds image
  |
  v
push to registry
  |
  v
deploy machine pulls image
  |
  v
docker compose up -d
```

6. Replace local auth.
   - Add real users.
   - Scope documents/chats/settings by user ID.
   - Add OAuth or managed auth provider.

Recommended migration order:

```text
1. Qdrant provider
2. PostgreSQL metadata repository
3. Storage provider
4. Separate worker/queue
5. Cloud backend deploy
6. Cloud frontend deploy
```

## 30. Operational Runbook

Local Docker:

```powershell
cd D:\RAG-chatbot
docker compose up -d
docker compose ps
```

Logs:

```powershell
docker compose logs -f backend
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8080/api/v1/health
```

Public quick demo:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

GitHub runner:

```powershell
cd D:\RAG-chatbot\actions-runner
.\run.cmd
```

If runner is installed as service:

```powershell
Get-Service actions.runner*
```

Preload reranker locally:

```powershell
.\.venv\Scripts\python.exe -m app.cli.preload_reranker --clean-incomplete
```
