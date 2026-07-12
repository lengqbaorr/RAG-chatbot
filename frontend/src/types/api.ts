export type HealthResponse = {
  app: string;
  database: string;
  embedding_service: string;
  vector_store: string;
  llm_provider: string;
  upload_dir: string | null;
  disk_free_bytes: number | null;
  collection: string | null;
  collection_count: number;
  pending_jobs: number;
  ready: boolean;
};

export type AuthStatusResponse = {
  enabled: boolean;
};

export type RuntimeSettingsResponse = {
  app_name: string;
  app_version: string;
  environment: string;
  auth_enabled: boolean;
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  llm_max_tokens: number;
  retrieval_strategy: "dense" | "parent_child";
  top_k: number;
  fetch_k: number;
  min_score: number;
  reranker_enabled: boolean;
  reranker_model: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;
  chroma_collection: string;
};

export type RuntimeSettingsUpdate = Partial<{
  llm_model: string;
  llm_temperature: number;
  llm_max_tokens: number;
  retrieval_strategy: "dense" | "parent_child";
  top_k: number;
  fetch_k: number;
  min_score: number;
  reranker_enabled: boolean;
  reranker_model: string;
}>;

export type AuthUser = {
  user_id: string;
  username: string;
  display_name: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
};

export type DocumentInfo = {
  source_id: string;
  source_name: string;
  source_type: string | null;
  chunk_count: number;
  status: string;
};

export type DocumentListResponse = {
  documents: DocumentInfo[];
};

export type DocumentUploadResponse = {
  job_id: string | null;
  source_id: string;
  status: string;
  duplicate: boolean;
  source_name?: string | null;
};

export type DocumentUrlUploadRequest = {
  url: string;
  title?: string;
};

export type DocumentDeleteResponse = {
  source_id: string;
  deleted_count: number;
  deleted_vectors: number;
  deleted_chunks: number;
  raw_file_deleted: boolean;
};

export type DocumentPreview = {
  source_id: string;
  source_name: string;
  source_type: string;
  mime_type: string | null;
  preview_kind: "pdf" | "text";
  page_count: number;
  content: string | null;
  truncated: boolean;
};

export type DocumentChunkPreview = {
  chunk_id: string;
  source_id: string;
  content: string;
  page_start: number | null;
  page_end: number | null;
  section_title: string | null;
  metadata: Record<string, unknown>;
};

export type JobInfo = {
  job_id: string;
  source_id: string;
  status: string;
  progress: number;
  current_stage: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type JobListResponse = {
  jobs: JobInfo[];
};

export type ChatRequest = {
  question: string;
  strategy: "dense" | "parent_child";
  top_k: number;
  fetch_k?: number;
  min_score?: number;
  temperature?: number;
  max_tokens?: number;
  model?: string;
  reranker_enabled?: boolean;
  reranker_model?: string;
  filters?: Record<string, unknown>;
  session_id?: string;
  selected_source_ids?: string[];
};

export type SourceCitation = {
  source_id: string;
  source_name: string;
  page_start: number | null;
  page_end: number | null;
  section_title: string | null;
  chunk_id: string;
  score: number;
  content_preview: string;
};

export type ChatResponse = {
  session_id: string | null;
  answer: string;
  sources: SourceCitation[];
  report: {
    retrieval_strategy: string;
    retrieval_results: number;
    context_sources: number;
    llm_provider: string | null;
    llm_model: string | null;
    llm_finish_reason: string | null;
    llm_prompt_tokens: number | null;
    llm_completion_tokens: number | null;
    llm_total_tokens: number | null;
    total_latency: number;
  };
};

export type ChatStreamEvent =
  | { event: "start"; data: { status: string; session_id: string } }
  | { event: "delta"; data: { text: string } }
  | { event: "complete"; data: ChatResponse }
  | { event: "error"; data: { code: string; message: string } };

export type ChatSession = {
  session_id: string;
  title: string;
  selected_source_ids: string[];
  created_at: string;
  updated_at: string;
};

export type ChatHistoryMessage = {
  message_id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceCitation[];
  selected_source_ids: string[];
  status: "completed" | "cancelled" | "failed";
  timestamp: string;
};

export type ChatSessionListResponse = { sessions: ChatSession[] };

export type ChatSessionDetailResponse = {
  session: ChatSession;
  messages: ChatHistoryMessage[];
};

export type ApiErrorPayload = {
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string | null;
  };
};
