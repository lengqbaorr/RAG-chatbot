from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from app.db import Database
from app.core.config import Settings, settings
from app.services.conversation import ConversationContextService
from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.chat_history import ChatHistoryRepository, ChatHistoryService
from app.services.embedding import (
    BGEM3EmbeddingProvider,
    EmbeddingConfig,
    EmbeddingService,
    SQLiteEmbeddingCache,
)
from app.services.health import HealthService
from app.services.indexing import (
    InMemoryIndexingQueue,
    IndexingConfig,
    IndexingPipeline,
    IndexingService,
    ThreadedIndexingWorker,
)
from app.services.ingestion import DocumentLoaderService
from app.services.document import DocumentRepository, DocumentService
from app.services.jobs import JobRepository, JobService
from app.services.llm import LLMConfig, LLMService
from app.services.rag import AnswerGenerator, RAGPipeline, RAGPipelineConfig
from app.services.reranking import CrossEncoderReranker, RerankerConfig, RerankerService
from app.services.retrieval import ParentChildRetrievalConfig, RetrievalConfig, RetrievalService
from app.services.settings import SettingsRepository, SettingsService
from app.services.vectorstore import ChromaVectorStore, VectorStoreConfig, VectorStoreService


def build_services(app: FastAPI, config: Settings = settings) -> None:
    Path(config.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(config.chroma_path).mkdir(parents=True, exist_ok=True)
    database = Database(config.metadata_db_path)
    database.initialize()
    document_repository = DocumentRepository(database)
    job_repository = JobRepository(database)
    job_service = JobService(job_repository)
    chat_history_repository = ChatHistoryRepository(database)
    chat_history_service = ChatHistoryService(chat_history_repository)
    conversation_context_service = ConversationContextService(chat_history_service)
    settings_repository = SettingsRepository(database)
    settings_service = SettingsService(repository=settings_repository, config=config)

    embedding_provider = BGEM3EmbeddingProvider(
        model_name=config.embedding_model,
        local_files_only=config.embedding_local_files_only,
    )
    embedding_config = EmbeddingConfig(
        model_name=config.embedding_model,
        dimension=config.embedding_dimension,
        batch_size=16,
        skip_retrieval_excluded=True,
        cache_enabled=True,
        cache_db_path=config.embedding_cache_path,
    )
    embedding_service = EmbeddingService(
        config=embedding_config,
        provider=embedding_provider,
        cache=SQLiteEmbeddingCache(config.embedding_cache_path),
    )

    vector_config = VectorStoreConfig(
        collection_name=config.chroma_collection,
        persist_directory=config.chroma_path,
        embedding_model=config.embedding_model,
        embedding_dimension=config.embedding_dimension,
        distance_metric="cosine",
        include_retrieval_excluded=False,
    )
    vector_store = ChromaVectorStore(
        collection_name=vector_config.collection_name,
        persist_directory=vector_config.persist_directory,
        embedding_dimension=vector_config.embedding_dimension,
        distance_metric=vector_config.distance_metric,
    )
    vector_store_service = VectorStoreService(config=vector_config, store=vector_store)

    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        dense_config=RetrievalConfig(
            top_k=config.default_top_k,
            fetch_k=config.default_fetch_k,
            min_score=config.default_min_score,
            filters={"content_type": "body", "chunk_level": "child"},
        ),
        parent_child_config=ParentChildRetrievalConfig(
            parent_top_k=config.default_top_k,
            child_fetch_k=config.default_fetch_k,
            min_score=config.default_min_score,
        ),
    )

    llm_service = LLMService(
        config=LLMConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
            timeout_seconds=int(config.http_timeout_seconds),
        )
    )
    rag_pipeline = RAGPipeline(
        retriever_service=retrieval_service,
        answer_generator=AnswerGenerator(llm_service=llm_service),
        reranker_service=RerankerService(
            CrossEncoderReranker(
                RerankerConfig(
                    model_name=config.reranker_model,
                    device=config.reranker_device,
                    local_files_only=config.reranker_local_files_only,
                )
            )
        ),
        config=RAGPipelineConfig(
            retrieval_strategy=config.default_retrieval_strategy,
            top_k=config.default_top_k,
            fetch_k=config.default_fetch_k,
            min_score=config.default_min_score,
            fallback_min_score=config.retrieval_fallback_min_score,
            enable_empty_retrieval_fallback=config.retrieval_fallback_enabled,
        ),
    )

    allowed = tuple(
        ext.strip().lower().lstrip(".")
        for ext in config.allowed_upload_extensions.split(",")
        if ext.strip()
    )
    queue = InMemoryIndexingQueue()
    indexing_pipeline = IndexingPipeline(
        loader=DocumentLoaderService(),
        chunker=DocumentChunker(
            config=ChunkingConfig(
                chunk_size_tokens=450,
                chunk_overlap_tokens=60,
                build_parent_chunks=True,
            )
        ),
        embedding_service=embedding_service,
        vector_store_service=vector_store_service,
        document_repository=document_repository,
        job_service=job_service,
    )
    indexing_service = IndexingService(
        document_repository=document_repository,
        job_service=job_service,
        queue=queue,
        config=IndexingConfig(
            upload_dir=config.upload_dir,
            max_upload_mb=config.max_upload_mb,
            allowed_extensions=allowed,
            duplicate_policy=config.duplicate_policy,
        ),
    )
    indexing_worker = ThreadedIndexingWorker(
        queue=queue,
        pipeline=indexing_pipeline,
        job_service=job_service,
        document_repository=document_repository,
    )
    indexing_worker.start()
    document_service = DocumentService(repository=document_repository, vector_store=vector_store)
    health_service = HealthService(
        vector_store=vector_store,
        llm_service=llm_service,
        embedding_service=embedding_service,
        database=database,
        job_service=job_service,
        upload_dir=config.upload_dir,
        reranker_service=rag_pipeline.reranker_service,
    )

    app.state.database = database
    app.state.document_repository = document_repository
    app.state.job_repository = job_repository
    app.state.job_service = job_service
    app.state.chat_history_repository = chat_history_repository
    app.state.chat_history_service = chat_history_service
    app.state.conversation_context_service = conversation_context_service
    app.state.settings_repository = settings_repository
    app.state.settings_service = settings_service
    app.state.embedding_service = embedding_service
    app.state.vector_store = vector_store
    app.state.vector_store_service = vector_store_service
    app.state.retrieval_service = retrieval_service
    app.state.llm_service = llm_service
    app.state.rag_pipeline = rag_pipeline
    app.state.reranker_service = rag_pipeline.reranker_service
    app.state.indexing_service = indexing_service
    app.state.indexing_worker = indexing_worker
    app.state.document_service = document_service
    app.state.health_service = health_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not settings.disable_startup:
        build_services(app, settings)
    try:
        yield
    finally:
        worker = getattr(app.state, "indexing_worker", None)
        if worker is not None:
            worker.stop()
