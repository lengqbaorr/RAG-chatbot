import pytest

from app.services.vectorstore.models import VectorRecord
from app.services.vectorstore.validators import (
    VectorStoreValidationError,
    VectorStoreValidator,
)


def _make_record(
    chunk_id: str = "c1",
    vector: list[float] | None = None,
    model: str = "BAAI/bge-m3",
    dim: int = 4,
    provider: str = "bge-m3",
) -> VectorRecord:
    return VectorRecord(
        chunk_id=chunk_id,
        document_id="d1",
        source_id="src_test",
        content="test",
        embedding_text="test",
        vector=vector or [0.1, 0.2, 0.3, 0.4],
        metadata={},
        source_name="test.pdf",
        source_type="pdf",
        content_type="body",
        chunk_level="child",
        embedding_provider=provider,
        embedding_model=model,
        embedding_dimension=dim,
        embedding_version="v1",
        embedding_text_hash="h1",
    )


class TestVectorStoreValidator:
    def test_valid_records_passes(self):
        validator = VectorStoreValidator()
        records = [_make_record(), _make_record(chunk_id="c2", vector=[0.5, 0.6, 0.7, 0.8])]
        validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_empty_records_raises(self):
        validator = VectorStoreValidator()
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records([], expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_dimension_mismatch_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(vector=[0.1, 0.2, 0.3])]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_model_mismatch_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(model="other-model")]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_dimension_in_record_mismatch_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(dim=999, vector=[0.1, 0.2, 0.3, 0.4])]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_nan_in_vector_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(vector=[0.1, float("nan")])]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_inf_in_vector_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(vector=[0.1, float("inf")])]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_empty_vector_raises(self):
        validator = VectorStoreValidator()
        records = [_make_record(vector=[0.0, float("nan")])]
        with pytest.raises(VectorStoreValidationError):
            validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)

    def test_zero_vector_passes_if_dim_correct(self):
        validator = VectorStoreValidator()
        records = [_make_record(vector=[0.0] * 4)]
        validator.validate_records(records, expected_model="BAAI/bge-m3", expected_dimension=4)
