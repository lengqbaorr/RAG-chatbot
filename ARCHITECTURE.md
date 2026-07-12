# RAG Chatbot Architecture

## 1. Product Overview

RAG Chatbot la ung dung hoi dap tai lieu ca nhan gom FastAPI backend va React frontend. He thong cho phep nguoi dung upload tai lieu, index tai lieu vao vector store, chon source can hoi, chat streaming voi LLM va xem lai citation/document preview.

Muc tieu kien truc hien tai:

- Frontend tach rieng backend.
- FastAPI chi la transport/interface layer.
- Business logic nam trong service layer.
- Khong dung LangChain/LlamaIndex lam core runtime.
- SQLite quan ly metadata nghiep vu.
- ChromaDB chi quan ly vector va metadata retrieval.
- Embedding/LLM/VectorStore deu nam sau provider/interface rieng.
- Chat history, document lifecycle va indexing job duoc luu rieng trong database.

## 2. System Diagram

```text
Browser
  |
  v
React + TypeScript + Vite
  |
  v
FastAPI
  |
  +-- Health API
  |
  +-- Document API
  |     |
  |     +-- DocumentService
  |     +-- DocumentRepository
  |     +-- SQLite metadata DB
  |
  +-- Upload/Reindex API
  |     |
  |     +-- IndexingService
  |     +-- IndexJobService
  |     +-- BackgroundWorker
  |     +-- Loader -> Chunker -> Embedding -> ChromaDB
  |
  +-- Chat API + SSE Stream API
  |     |
  |     +-- ChatHistoryService
  |     +-- RAGPipeline
  |           |
  |           +-- RetrieverService
  |           +-- ContextBuilder
  |           +-- PromptBuilder
  |           +-- LLMService / GeminiProvider
  |           +-- CitationBuilder
  |
  +-- Jobs API
        |
        +-- JobService
        +-- SQLite metadata DB
```

## 3. Runtime Stack

Backend:

- FastAPI
- SQLite metadata database
- ChromaDB vector database
- BGE-M3 embedding provider
- Gemini LLM provider
- Tesseract OCR
- Background indexing worker

Frontend:

- React
- TypeScript
- Vite
- TailwindCSS
- TanStack Query
- Zustand
- React Router
- Framer Motion
- React Markdown

## 4. Backend Entry Points

Primary app entry:

- `app/main.py`
- `app/api/main.py`

FastAPI registers the same routes at root and `/api/v1`:

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

## 5. Core Backend Layers

### 5.1 API Layer

Location:

- `app/api/routes`
- `app/api/schemas`
- `app/api/dependencies.py`

Responsibility:

- Validate HTTP input.
- Convert request/response schemas.
- Resolve services through dependency injection.
- Return stable API contracts for frontend.

Routes do not call ChromaDB, Gemini, BGE-M3, chunker or loader directly.

### 5.2 Core Layer

Location:

- `app/core/config.py`
- `app/core/startup.py`
- `app/core/logging.py`
- `app/core/exceptions.py`

Responsibility:

- Load `.env` settings.
- Initialize singleton services on lifespan startup.
- Configure CORS.
- Install request logging middleware.
- Register exception-to-HTTP mappings.

### 5.3 Database Layer

Location:

- `app/db/database.py`
- `app/db/migrations`

SQLite is the current metadata store. It stores product/domain data, not embeddings.

Main tables:

- `documents`
- `chunks`
- `index_jobs`
- `chat_sessions`
- `chat_messages`

The database initializer also performs lightweight compatible migrations for existing local DB files.

## 6. Document Management

Location:

- `app/services/document`

Main classes:

- `DocumentRepository`
- `DocumentService`
- `DocumentRecord`
- `ChunkRecord`
- `DocumentPreview`
- `DocumentChunkPreview`

Responsibility:

- Manage document metadata.
- Track status: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `DELETED`.
- List documents for frontend.
- Get document detail.
- Delete document safely.
- Provide document preview and citation chunk preview.
- Store chunk metadata and chunk content for preview.

ChromaDB is not the source of truth for document lifecycle.

### 6.1 Document Metadata

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

### 6.2 Chunk Metadata

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

`content` is stored so text previews can be loaded from SQLite without re-parsing files.

## 7. Document Preview

Preview endpoints:

- `GET /documents/{source_id}/preview`
- `GET /documents/{source_id}/chunks/{chunk_id}`
- `GET /documents/{source_id}/file`

Behavior:

- PDF opens through `/file` and browser PDF viewer.
- URL PDF redirects to the original remote URL.
- Text-like documents use stored chunk text.
- Legacy non-PDF documents can fallback to loader-based preview.
- Retrieved chunk is returned separately and highlighted in frontend.

Current limitation:

- PDF preview opens the correct page, but does not highlight exact PDF coordinates because bounding boxes are not stored yet.

## 8. Indexing Platform

Location:

- `app/services/indexing`
- `app/services/jobs`

Upload/indexing flow:

```text
Upload file or URL
  |
  v
Validate and save raw input
  |
  v
Create document record
  |
  v
Create index job
  |
  v
Background worker
  |
  +-- Loading
  +-- Chunking
  +-- Embedding
  +-- VectorStore upsert
  +-- Save chunk metadata
  +-- Mark document/job completed
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

Duplicate detection uses:

- `sha256`
- `file_size`

## 9. Loader Layer

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

- Tesseract
- English and Vietnamese language data

The loader returns normalized internal documents. It does not embed or store vectors.

## 10. Chunking Pipeline

Location:

- `app/services/chunking`

Responsibilities:

- Normalize document text.
- Parse structure and headings.
- Detect content type such as body, cover, toc, reference and table.
- Build child chunks.
- Build parent chunks for parent-child retrieval.
- Validate token budget.
- Generate quality metadata.

Important behaviors:

- Cover/toc/reference chunks can be excluded from retrieval.
- Section heading context is added to embedding text.
- Parent-child chunks preserve source/page/citation metadata.

## 11. Embedding Layer

Location:

- `app/services/embedding`

Main provider:

- BGE-M3

Responsibilities:

- Embed documents/chunks.
- Embed user query.
- Validate vector dimension.
- Cache embeddings in SQLite.
- Hide provider details behind service/provider interface.

Embedding cache reduces repeated indexing cost when content hash/model version has not changed.

## 12. VectorStore Layer

Location:

- `app/services/vectorstore`

Main implementation:

- ChromaDB

Responsibilities:

- Upsert embedded chunks.
- Similarity search.
- Delete by `source_id`.
- Fetch vector record by `chunk_id`.
- Apply neutral metadata filters from retriever.

ChromaDB stores:

- vector
- retrieval metadata
- chunk content needed for retrieval/preview fallback

ChromaDB does not manage:

- document status
- indexing jobs
- chat history
- product metadata

## 13. Retrieval Layer

Location:

- `app/services/retrieval`

Main strategies:

- `DenseRetriever`
- `ParentChildRetriever`

Pipeline:

```text
User query
  |
  v
QueryPreprocessor
  |
  v
EmbeddingService.embed_query
  |
  v
VectorStore similarity_search
  |
  v
Threshold / ContentType filter
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

Retriever only depends on:

- `EmbeddingService`
- `BaseVectorStore`

Retriever does not call:

- LLM
- PromptBuilder
- FastAPI
- Chroma SDK directly

## 14. Reranking and Evaluation

Location:

- `app/services/reranking`
- `app/services/evaluation`

Reranking:

- Optional layer after retrieval.
- Keeps original retrieval score.
- Adds rerank score.
- Does not call vector store or LLM.

Evaluation:

- Loads local evaluation dataset.
- Computes retrieval metrics.
- Supports Recall@K, Precision@K, MRR, citation accuracy and keyword coverage.
- Does not use LLM as judge in baseline.

## 15. RAG Answer Pipeline

Location:

- `app/services/rag`
- `app/services/llm`

Pipeline:

```text
Question
  |
  v
RetrieverService
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

Current LLM provider:

- Gemini

Provider boundary:

- `BaseLLMProvider`
- `GeminiProvider`
- `OpenRouterProvider`
- `OllamaProvider`

PromptBuilder does not call LLM. LLMProvider does not know retriever/vector store.

## 16. Streaming Chat

Endpoint:

- `POST /chat/stream`

Transport:

- Server-Sent Events

Events:

- `start`
- `delta`
- `complete`
- `error`

Behavior:

- Backend streams LLM text chunks.
- Frontend renders with a typewriter effect for word/character-level perceived realtime.
- User can cancel request through AbortController.
- Final `complete` event carries answer, sources and report.
- Sources are shown in the Sources panel, not inline inside the answer.

## 17. Local Authentication

Location:

- `app/services/auth`
- `app/api/routes/auth.py`
- `frontend/src/store/authStore.ts`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/layout/AuthGate.tsx`

Current auth mode:

- Single local user.
- Optional through `AUTH_ENABLED`.
- Username/password are read from `.env`.
- Backend issues a signed HMAC bearer token with expiration.
- Frontend stores token in local storage and sends `Authorization: Bearer ...`.

Public endpoints:

- `/health`
- `/health/ready`
- `/auth/status`
- `/auth/login`

Protected product endpoints:

- documents
- jobs
- chat
- chat sessions

This is a baseline security layer for local/private deployment. It prepares the codebase for future multi-user auth by keeping auth at the API/dependency boundary.

## 18. Chat History

Location:

- `app/services/chat_history`
- `app/api/routes/chat_sessions.py`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/chat/ChatWindow.tsx`

Backend stores:

- chat sessions
- user messages
- assistant messages
- selected documents
- sources/citations
- message status
- timestamps

Message status:

- `completed`
- `cancelled`
- `failed`

Frontend supports:

- New chat
- Load previous session
- Rename session
- Delete session
- Persist messages after browser refresh
- Restore selected documents for a session
- Show cancelled/failed warning for historical assistant messages

## 19. Frontend Architecture

Location:

- `frontend/src/api`
- `frontend/src/hooks`
- `frontend/src/store`
- `frontend/src/components`
- `frontend/src/pages`
- `frontend/src/types`

Responsibilities:

- API client wraps backend endpoints.
- TanStack Query handles server state.
- Zustand handles UI/client state.
- Components stay small and reusable.
- Pages compose feature components.

Main screens:

- Dashboard
- Documents
- Jobs
- Chat
- Settings

Chat UI:

- Left sidebar: navigation and chat history.
- Center: conversation.
- Right panel: selected sources and retrieved citations.
- Modal: document preview.

## 20. Source Selection and Citations

User selects documents in the Sources panel. Selection behavior:

- Tick means include the document.
- Untick means exclude only that document.
- Toggling one document does not auto-select the others.

Chat request passes:

- `selected_source_ids`
- neutral `filters.source_id`

Backend also intersects requested source IDs with completed documents, so failed/running/deleted documents are not retrieved.

Retrieved citations are returned as structured objects:

- `source_id`
- `source_name`
- `page_start`
- `page_end`
- `section_title`
- `chunk_id`
- `score`
- `content_preview`

## 21. Health and Observability

Health endpoints report:

- app status
- database status
- embedding service status
- vector store status
- LLM provider
- upload directory
- free disk space
- Chroma collection
- collection count
- pending jobs
- ready flag

Logging includes:

- request latency
- request ID
- endpoint
- source ID/job ID when available
- retrieval strategy
- number of sources
- stack trace for errors

Secrets and full document content are not logged.

## 22. Current Production Boundaries

What is production-ready baseline:

- Document metadata is not stored only in Chroma.
- Upload/indexing has job lifecycle.
- Chat uses streaming and persistent session history.
- Source selection is explicit.
- Citation preview works for PDF/text-like documents.
- Tests cover core API/service flows.

Known limitations:

- SQLite is suitable for local/single-user baseline, not high-concurrency SaaS.
- Background worker is local process/thread based.
- File storage is local disk.
- PDF preview does not yet store bounding boxes for exact highlight.
- Authentication is local single-user baseline, not OAuth/multi-user yet.
- Reranker exists but is not wired as the default product chat path.

## 23. Upgrade Path

PostgreSQL:

- Keep repository contracts.
- Replace SQLite connection/repository internals.
- Add Alembic migrations.

Redis/Celery/RQ:

- Keep `IndexingService` and `IndexJobService`.
- Replace local worker/queue implementation.

S3/Object Storage:

- Keep `raw_path` as storage locator.
- Add storage provider interface.
- Replace local disk save/delete logic.

Auth/Multi-tenant:

- Use `owner` on documents and chat sessions.
- Scope list/search/delete by user ID.
- Add auth dependency at API layer.

Deployment:

- Backend container.
- Frontend static build served by Nginx.
- Persistent volumes for Chroma, SQLite/PostgreSQL and raw uploads.
- Health checks for backend and worker.
