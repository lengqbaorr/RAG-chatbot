CREATE TABLE documents (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    raw_path TEXT NOT NULL,
    upload_time TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT,
    language TEXT,
    page_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    embedding_model TEXT,
    embedding_dimension INTEGER,
    collection_name TEXT,
    deleted_at TEXT
);

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    parent_id TEXT,
    content TEXT NOT NULL DEFAULT '',
    page_start INTEGER,
    page_end INTEGER,
    section_title TEXT,
    header_path TEXT,
    token_count INTEGER NOT NULL,
    retrieval_excluded INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL
);

CREATE TABLE index_jobs (
    job_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    current_stage TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    owner TEXT,
    selected_source_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE chat_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources TEXT NOT NULL DEFAULT '[]',
    selected_source_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'completed',
    timestamp TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE user_settings (
    owner TEXT PRIMARY KEY,
    settings_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
