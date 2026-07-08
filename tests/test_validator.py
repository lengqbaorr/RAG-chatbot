import pytest

from app.schemas.chunk import ChunkMetadata, ChunkingStrategy, DocumentChunk
from app.schemas.document import DocumentType
from app.services.embedding.models import EmbeddingInput
from app.services.embedding.validator import (
    EmbeddingValidationError,
    EmbeddingValidator,
)


def _make_input(text: str = "content", embedding_text: str | None = None) -> EmbeddingInput:
    return EmbeddingInput(
        chunk=DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            source_id="s1",
            text=text,
            chunk_index=0,
            token_count=5,
            content_hash="h1",
            metadata=ChunkMetadata(
                source_id="s1",
                source_name="test",
                source_type=DocumentType.txt,
                chunk_index=0,
                token_count=5,
                content_hash="h1",
                embedding_text_hash="",
                chunk_strategy=ChunkingStrategy.recursive_token,
            ),
        ),
        embedding_text=embedding_text if embedding_text is not None else text,
        embedding_text_hash="hash",
    )


class TestEmbeddingValidator:
    def test_valid_batch_passes(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a"), _make_input("b")]
        vectors = [[0.1, 0.2], [0.3, 0.4]]
        validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_empty_vector_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a")]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch([[]], inputs, expected_dimension=2)

    def test_dimension_mismatch_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a")]
        vectors = [[0.1, 0.2, 0.3]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_nan_in_vector_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a")]
        vectors = [[0.1, float("nan")]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_inf_in_vector_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a")]
        vectors = [[0.1, float("inf")]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_negative_inf_in_vector_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a")]
        vectors = [[0.1, float("-inf")]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_count_mismatch_raises(self):
        validator = EmbeddingValidator()
        inputs = [_make_input("a"), _make_input("b")]
        vectors = [[0.1, 0.2]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, inputs, expected_dimension=2)

    def test_empty_embedding_text_raises(self):
        validator = EmbeddingValidator()
        inp = _make_input("content", embedding_text="non-empty")
        empty_input = inp.model_copy(update={"embedding_text": ""})
        vectors = [[0.1, 0.2]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, [empty_input], expected_dimension=2)

    def test_missing_metadata_raises(self):
        validator = EmbeddingValidator()
        inp = _make_input("content")
        no_meta = inp.model_copy(update={"chunk": inp.chunk.model_copy(update={"metadata": None})})
        vectors = [[0.1, 0.2]]
        with pytest.raises(EmbeddingValidationError):
            validator.validate_batch(vectors, [no_meta], expected_dimension=2)
