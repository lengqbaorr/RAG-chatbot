from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import Settings, settings
from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.embedding import (
    BGEM3EmbeddingProvider,
    EmbeddingConfig,
    EmbeddingService,
    SQLiteEmbeddingCache,
)
from app.services.health import HealthService
from app.services.indexing import IndexingConfig, IndexingService
from app.services.ingestion import DocumentLoaderService
from app.services.llm import LLMConfig, LLMService
from app.services.rag import AnswerGenerator, RAGPipeline, RAGPipelineConfig
from app.services.retrieval import ParentChildRetrievalConfig, RetrievalConfig, RetrievalService
from app.services.vectorstore import ChromaVectorStore, VectorStoreConfig, VectorStoreService
from app.services.documents import DocumentManagementService


def build_services(app: FastAPI, config: Settings = settings) -> None:
    Path(config.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(config.chroma_path).mkdir(parents=True, exist_ok=True)

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
        config=RAGPipelineConfig(
            retrieval_strategy=config.default_retrieval_strategy,
            top_k=config.default_top_k,
            fetch_k=config.default_fetch_k,
            min_score=config.default_min_score,
        ),
    )

    allowed = tuple(
        ext.strip().lower().lstrip(".")
        for ext in config.allowed_upload_extensions.split(",")
        if ext.strip()
    )
    indexing_service = IndexingService(
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
        config=IndexingConfig(
            upload_dir=config.upload_dir,
            max_upload_mb=config.max_upload_mb,
            allowed_extensions=allowed,
        ),
    )
    document_service = DocumentManagementService(vector_store=vector_store)
    health_service = HealthService(
        vector_store=vector_store,
        llm_service=llm_service,
        embedding_service=embedding_service,
    )

    app.state.embedding_service = embedding_service
    app.state.vector_store = vector_store
    app.state.vector_store_service = vector_store_service
    app.state.retrieval_service = retrieval_service
    app.state.llm_service = llm_service
    app.state.rag_pipeline = rag_pipeline
    app.state.indexing_service = indexing_service
    app.state.document_service = document_service
    app.state.health_service = health_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not settings.disable_startup:
        build_services(app, settings)
    yield
