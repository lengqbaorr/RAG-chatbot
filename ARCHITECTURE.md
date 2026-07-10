# RAG Chatbot Architecture Report

## 1. Tong quan san pham

RAG Chatbot la he thong hoi dap tai lieu ca nhan theo kien truc Retrieval-Augmented Generation. San pham cho phep nguoi dung upload tai lieu, he thong tu dong index tai lieu, sau do nguoi dung co the chon nguon tai lieu va dat cau hoi tren frontend.

Muc tieu kien truc hien tai:

- Tach ro frontend, API transport layer va business logic.
- Khong dung LangChain/LlamaIndex lam core runtime.
- Khong dung ChromaDB lam document database.
- Luu metadata nghiep vu rieng trong SQLite.
- ChromaDB chi luu vector va metadata phuc vu retrieval.
- Tat ca model provider nhu embedding va LLM duoc boc sau service/provider interface.
- Co nen tang de nang cap len PostgreSQL, queue worker, object storage, auth va multi-tenant.

## 2. So do tong the

```text
Browser
  |
  v
React Frontend
  |
  v
FastAPI Interface Layer
  |
  +-- Document API --------> Document Service ----> SQLite metadata DB
  |
  +-- Job API -------------> Job Service ---------> SQLite metadata DB
  |
  +-- Upload API ----------> Indexing Service ----> Background Worker
  |                                                   |
  |                                                   v
  |                                             Loader / Chunker
  |                                                   |
  |                                                   v
  |                                             Embedding Service
  |                                                   |
  |                                                   v
  |                                             ChromaDB VectorStore
  |
  +-- Chat API -----------> RAG Pipeline
                              |
                              v
                        Retriever Service
                              |
                              v
                        ContextBuilder
                              |
                              v
                        PromptBuilder
                              |
                              v
                        LLMService / Gemini
                              |
                              v
                        CitationBuilder
```

## 3. Backend module architecture

### 3.1 `app/api`

Day la Interface Layer cua backend. Endpoint chi lam cac viec:

- Nhan HTTP request.
- Validate request schema.
- Goi service/pipeline tu dependency injection.
- Tra response schema on dinh cho frontend.

Endpoint khong duoc goi truc tiep ChromaDB, BGE-M3, Gemini, chunker internals hoac loader internals.

Routes hien tai:

- `GET /health`
- `GET /health/ready`
- `POST /documents/upload`
- `GET /documents`
- `GET /documents/{source_id}`
- `DELETE /documents/{source_id}`
- `POST /documents/reindex/{source_id}`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /chat`

`/chat/stream` chua phai product path hien tai. Chat dang dung non-streaming response.

### 3.2 `app/core`

Chua cac thanh phan nen tang dung chung:

- `config.py`: doc `.env`, cau hinh app, database, upload, ChromaDB, embedding, LLM, CORS.
- `logging.py`: middleware logging request, latency, error stack trace.
- `exceptions.py`: custom exception va mapping loi.
- `startup.py`: khoi tao service singleton khi app startup.

Nguyen tac: config va lifecycle nam o core, khong nam trong route handler.

### 3.3 `app/db`

Quan ly database metadata.

- `database.py`: khoi tao SQLite schema va migration tuong thich voi DB cu.
- `sqlite.py`: ket noi SQLite.
- `postgres.py`: placeholder/adapter cho PostgreSQL sau nay.

SQLite hien la metadata store chinh cho document, chunk va job. Khi nang cap PostgreSQL, repository contract giu nguyen de han che thay doi business logic.

### 3.4 `app/schemas`

Chua schema noi bo cho document/chunk duoc cac service su dung. API schema rieng nam trong `app/api/schemas`, khong expose truc tiep internal model neu khong can.

## 4. Document Management Platform

### 4.1 Muc tieu

Document Management Platform tach document lifecycle khoi vector database. Metadata nghiep vu duoc quan ly trong SQLite, con ChromaDB chi la vector index.

Dieu nay giup:

- List document khong phu thuoc Chroma query.
- Delete document khong bi xoa nham page-level metadata.
- Theo doi status indexing ro rang.
- Ho tro duplicate detection.
- De mo rong sang PostgreSQL/S3/multi-user.

### 4.2 `app/services/document`

Trach nhiem:

- Quan ly metadata document.
- Validate file upload.
- CRUD document theo `source_id`.
- List document cho frontend.
- Tim document theo hash/filename de detect duplicate.

File chinh:

- `models.py`: model document, status, metadata.
- `repository.py`: thao tac DB thuan tuy, khong biet loader/Chroma/Gemini.
- `service.py`: orchestration cap document.
- `validators.py`: validate extension, size, filename an toan.
- `metadata_store.py`: adapter metadata store.

### 4.3 Document metadata

Metadata document luu cac truong chinh:

- `source_id`: ID nghiep vu duy nhat cua tai lieu.
- `source_name`: ten hien thi.
- `original_filename`: ten file goc.
- `mime_type`: MIME type.
- `file_size`: kich thuoc file.
- `sha256`: hash phuc vu duplicate detection.
- `raw_path`: duong dan file raw da luu.
- `upload_time`: thoi diem upload.
- `status`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `DELETED`.
- `language`: ngon ngu tai lieu.
- `page_count`: so page/document units.
- `chunk_count`: so chunk.
- `embedding_model`: model embedding dung de index.
- `embedding_dimension`: dimension vector.
- `collection_name`: Chroma collection.
- `deleted_at`: soft delete marker.

### 4.4 Chunk metadata

Chunk metadata luu trong DB rieng de phuc vu document detail, audit va re-index:

- `chunk_id`
- `source_id`
- `parent_id`
- `page_start`
- `page_end`
- `section_title`
- `header_path`
- `token_count`
- `retrieval_excluded`
- `content_hash`

## 5. Indexing Platform

### 5.1 Indexing flow

```text
Upload file
  |
  v
Save raw file safely
  |
  v
Create Document record
  |
  v
Create IndexJob
  |
  v
Background Worker
  |
  +--> Loading
  +--> Chunking
  +--> Embedding
  +--> VectorStore upsert
  +--> Metadata update
  +--> Job completed
```

### 5.2 `app/services/indexing`

Trach nhiem:

- Dieu phoi toan bo indexing pipeline.
- Gan `source_id` cua metadata platform vao moi chunk/vector.
- Cap nhat progress job theo stage.
- Upsert vector vao ChromaDB.
- Luu chunk metadata vao SQLite.
- Xu ly loi va cap nhat job/document status.

File chinh:

- `models.py`: request/result/status cua indexing.
- `service.py`: submit upload/reindex tu API.
- `pipeline.py`: logic loading -> chunking -> embedding -> vectorstore -> metadata.
- `worker.py`: background worker baseline bang thread.
- `queue.py`: queue abstraction de sau nay thay bang Celery/RQ/Dramatiq.
- `progress.py`: progress va current stage.

### 5.3 Job lifecycle

Job status:

- `PENDING`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

Stage chinh:

- `Uploading`
- `Loading`
- `Chunking`
- `Embedding`
- `VectorStore`
- `Finishing`

## 6. Ingestion Layer

`app/services/ingestion` la loader layer cho nhieu loai input.

Ho tro hien tai:

- PDF
- DOCX
- TXT
- Markdown
- URL/HTML
- Image/OCR voi Tesseract

Loader chuyen input ve document units co content va metadata ban dau. Loader khong chunk, khong embedding va khong ghi vector DB.

## 7. Chunking Layer

`app/services/chunking` chiu trach nhiem bien document units thanh chunk phu hop cho retrieval.

Pipeline logic:

```text
Document
  |
  v
Normalizer
  |
  v
Structure Parser
  |
  v
Chunk Splitter
  |
  v
Post Processor
  |
  v
Validator
  |
  v
DocumentChunk
```

Tinh nang chinh:

- Token-aware chunking.
- Metadata day du page, section, header path.
- Content type detection: body, cover, toc, reference, table.
- Retrieval exclusion cho cover/toc/reference khi can.
- Parent-child chunking.
- Merge small chunks.
- Heading context duoc them vao content embedding.
- Quality report cho token distribution, duplicate, excluded chunks.

Parent-child strategy:

- Child chunk dung de search.
- Parent chunk dung lam context dai hon cho LLM.
- Citation van giu page/source cua chunk lien quan.

## 8. Embedding Layer

`app/services/embedding` boc embedding provider sau service interface.

Thanh phan chinh:

- `EmbeddingService`: API noi bo cho embed document/query.
- `BGE-M3 Provider`: provider chinh hien tai.
- `OpenAI Provider`: optional adapter.
- SQLite embedding cache: tranh embed lai content da co hash.
- Validation va normalization vector.

Nguyen tac:

- Retriever khong biet model embedding cu the.
- API khong load model truc tiep.
- Model duoc khoi tao qua startup/dependency, khong khoi tao moi moi request.

## 9. VectorStore Layer

`app/services/vectorstore` truu tuong hoa vector database.

Provider hien tai:

- `ChromaVectorStore`

Vai tro:

- Upsert embedded chunks.
- Similarity search.
- Delete theo `source_id`.
- Count collection.
- Boc filter syntax de khong expose ChromaDB API ra ngoai.

ChromaDB chi luu:

- Vector.
- Content can retrieval.
- Metadata phuc vu filter/citation.

ChromaDB khong la source of truth cho document lifecycle.

## 10. Retrieval Layer

`app/services/retrieval` chiu trach nhiem lay context ung vien tu vector store.

Pipeline:

```text
User Query
  |
  v
QueryPreprocessor
  |
  v
EmbeddingService.embed_query()
  |
  v
Retriever
  |
  v
VectorStore.similarity_search()
  |
  v
PostProcessor / Filter / Deduplicator
  |
  v
RetrievedContext
```

Thanh phan:

- `query_preprocessor.py`: normalize whitespace/punctuation, giu tieng Viet, so, ma, section number.
- `retrievers/dense_retriever.py`: dense retrieval baseline.
- `retrievers/parent_child_retriever.py`: search child, expand parent.
- `filters.py`: score threshold, content type, metadata filter.
- `deduplicator.py`: dedup theo chunk_id, parent_id, content hash, source page.
- `context_selector.py`: chon top_k cuoi cung.
- `postprocessor.py`: pipeline filter/dedup/select.
- `service.py`: routing strategy `dense` hoac `parent_child`.

Product path hien tai khong dung reranker. Reranking/evaluation da duoc tach khoi runtime product de giu codebase gon.

## 11. RAG Layer

`app/services/rag` la answer pipeline cap cao.

Pipeline:

```text
Question
  |
  v
RetrieverService.retrieve()
  |
  v
ContextBuilder.build()
  |
  v
PromptBuilder.build()
  |
  v
LLMService.generate()
  |
  v
CitationBuilder.build()
  |
  v
RAGAnswer
```

Thanh phan:

- `context_builder.py`: format context block, gioi han token budget, giu source metadata.
- `prompt_builder.py`: tao system/user prompt, bat buoc tra loi dua tren context.
- `answer_generator.py`: dieu phoi context -> prompt -> LLM.
- `citation_builder.py`: tao danh sach citation song song voi answer.
- `pipeline.py`: orchestration end-to-end.
- `models.py`: `RAGAnswer`, `RAGReport`, citation, context models.

RAG layer khong biet ChromaDB SDK. RAG layer chi biet retriever, context builder, prompt builder, LLM service va citation builder.

## 12. LLM Layer

`app/services/llm` boc LLM sau provider interface.

Provider hien tai:

- `GeminiProvider`: provider chinh.
- `OpenRouterProvider`: optional.
- `OllamaProvider`: optional local fallback.

Thanh phan:

- `BaseLLMProvider`: interface generate/stream/default_model/provider_name.
- `LLMService`: route request den provider, validate config, log latency.
- `LLMRequest`, `LLMResponse`, `LLMUsage`: schema noi bo.

Nguyen tac:

- Provider khong build prompt.
- Provider khong biet Retriever.
- Provider khong biet VectorStore.
- Gemini SDK/REST detail chi nam trong `gemini_provider.py`.

Mac dinh product hien tai dung `gemini-2.5-flash` va `LLM_MAX_TOKENS=2048`.

## 13. Chat API behavior

`POST /chat` nhan:

- `question`
- `strategy`
- `top_k`
- `min_score`
- `filters`

Chat route chi search tren document co status `COMPLETED`.

Neu frontend chon source cu the, request gui filter:

```json
{
  "filters": {
    "source_id": {
      "$in": ["source_id_1", "source_id_2"]
    }
  }
}
```

Backend se intersect filter nay voi danh sach completed documents de tranh chat vao document chua index xong hoac da bi xoa.

Response gom:

- `answer`
- `sources`
- `report`

Report co thong tin retrieval strategy, so source, LLM provider/model, latency, finish reason va token usage neu provider tra ve.

## 14. Frontend architecture

Frontend nam trong `frontend/`, dung React + TypeScript + Vite.

Thu vien chinh:

- React 19
- TypeScript strict
- TailwindCSS
- TanStack Query
- React Router
- Zustand
- React Markdown
- Syntax Highlight
- Framer Motion
- lucide-react

### 14.1 Folder structure

```text
frontend/src
  api/          HTTP client va endpoint functions
  hooks/        TanStack Query hooks va UI logic hooks
  services/     frontend service helpers
  store/        Zustand stores
  components/   UI components theo domain
  pages/        Dashboard, Documents, Jobs, Chat, Settings
  routes/       Route definitions
  styles/       global styles/theme
  utils/        utility functions
  types/        shared TypeScript types
  assets/       static assets
```

### 14.2 Frontend responsibilities

- Dashboard hien health/system status.
- Documents page hien list tai lieu, upload, delete, reindex.
- Jobs page hien indexing progress.
- Chat page cung cap conversation UI.
- Source sidebar hien tat ca document da upload.
- Nguoi dung tick document trong source sidebar de gioi han pham vi chat.
- Settings page cho cac tham so retrieval/LLM co the thay doi tu UI.

Frontend khong biet business logic chunking, embedding, vectorstore hay LLM provider. Frontend chi goi API contract on dinh.

## 15. Storage architecture

### 15.1 SQLite metadata DB

Duong dan mac dinh: `data/metadata.db`

Luu:

- Documents.
- Chunks metadata.
- Index jobs.
- Chat session/message schema de san.

### 15.2 ChromaDB

Duong dan mac dinh: `data/chroma`

Luu:

- Vector embeddings.
- Chunk content phuc vu retrieval.
- Retrieval metadata.

Delete document phai xoa ca metadata DB, Chroma vectors va raw file de tranh orphan data.

### 15.3 Embedding cache

Duong dan mac dinh: `data/embeddings.db`

Luu cache embedding theo content hash/model/version de tranh tinh lai vector khong can thiet.

### 15.4 Raw files

Duong dan mac dinh: `data/raw`

File upload duoc luu bang safe filename/internal source ID. Thu muc data duoc ignore de tranh push tai lieu rieng tu len GitHub.

## 16. Security va data hygiene

Hien tai da ap dung cac nguyen tac:

- `.env` khong duoc commit.
- API key khong log ra response.
- Raw documents va local databases nam trong `data/` va duoc ignore.
- Upload validate extension, size va safe filename.
- Khong log full document content.
- CORS cho frontend dev origin.
- Endpoint khong expose internal SDK exception truc tiep nhu product API contract.

Can bo sung khi len production public:

- Authentication/authorization.
- Per-user ownership/tenant filter.
- Rate limiting.
- File malware scanning.
- Audit log.
- Object storage thay vi local filesystem.
- Secret manager thay vi `.env`.

## 17. Current runtime workflow

### 17.1 Chay local product

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

### 17.2 Upload to indexing

```text
User uploads file in frontend
  |
  v
POST /documents/upload
  |
  v
Create document + job
  |
  v
Worker indexes in background
  |
  v
GET /jobs shows progress
  |
  v
Document status becomes COMPLETED
```

### 17.3 Chat with selected sources

```text
User ticks documents in source sidebar
  |
  v
Frontend sends /chat with source_id filter
  |
  v
Backend validates completed documents
  |
  v
Parent-child retriever searches Chroma
  |
  v
ContextBuilder builds source blocks
  |
  v
Gemini generates answer
  |
  v
CitationBuilder returns sources
```

## 18. Product readiness assessment

He thong hien tai da dat muc production-ready baseline cho local/private RAG product:

- Co backend API ro rang.
- Co frontend dung duoc hang ngay.
- Co document management rieng.
- Co background indexing jobs.
- Co metadata store rieng.
- Co vector store abstraction.
- Co embedding cache.
- Co RAG pipeline end-to-end.
- Co citation va source selection.
- Co health monitoring.
- Co test suite backend va build frontend.

Chua phai production SaaS public vi con thieu:

- Streaming token-by-token.
- Auth va multi-user isolation.
- Persistent chat history UI/backend integration day du.
- External background queue.
- PostgreSQL migration thuc te.
- Object storage.
- Deployment hardening.
- Observability stack.

## 19. Gioi han hien tai

- Chat dang dung `/chat` non-streaming, nen cau tra loi chi hien sau khi LLM tra ve xong.
- Reranker khong nam trong product path hien tai sau dot clean code.
- Evaluation framework da duoc xoa khoi runtime product; neu can eval sau nay nen tao lai thanh module/tool rieng, tach khoi app production.
- SQLite phu hop local/dev/single-user. Production multi-user nen dung PostgreSQL.
- Background worker baseline dung thread/in-process. Production nen dung Redis Queue/Celery/RQ/Dramatiq.
- Raw file dang luu local. Production nen dung S3-compatible object storage.

## 20. Huong nang cap tiep theo

Thu tu nen uu tien:

1. Streaming chat: them `/chat/stream`, LLM streaming provider va frontend SSE renderer.
2. Chat sessions: luu conversation vao DB va hien history dung product.
3. Auth: user account, ownership, source filter theo user.
4. Queue production: tach indexing worker ra process rieng voi Redis/Celery/RQ.
5. PostgreSQL: migrate metadata store sang PostgreSQL.
6. Object storage: luu raw file vao S3/MinIO.
7. Observability: structured logs, metrics, tracing.
8. Deployment: Docker Compose, Nginx, health checks, environment profiles.

## 21. Nguyen tac kien truc can giu

- FastAPI la transport layer, khong chua business logic.
- Repository chi thao tac DB, khong biet loader/vectorstore/LLM.
- ChromaDB khong quan ly document lifecycle.
- Embedding va LLM luon qua service/provider interface.
- Retriever khong goi LLM.
- LLM provider khong build prompt.
- ContextBuilder khong goi LLM.
- Frontend chi phu thuoc API contract, khong phu thuoc implementation backend.
- Moi nang cap production nen giu contract API on dinh de frontend khong bi vo.
