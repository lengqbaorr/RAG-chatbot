import math
import warnings

from app.services.vectorstore.models import VectorRecord


class VectorStoreValidationError(Exception):
    pass


class VectorStoreValidator:
    def validate_records(
        self,
        records: list[VectorRecord],
        expected_model: str,
        expected_dimension: int,
    ) -> None:
        if not records:
            msg = "Records list is empty"
            warnings.warn(msg)
            raise VectorStoreValidationError(msg)

        for idx, rec in enumerate(records):
            self._validate_vector(rec.vector, expected_dimension, idx)

        for idx, rec in enumerate(records):
            if rec.embedding_model != expected_model:
                msg = (
                    f"Record at index {idx} has embedding_model "
                    f"'{rec.embedding_model}', expected '{expected_model}'"
                )
                warnings.warn(msg)
                raise VectorStoreValidationError(msg)

            if rec.embedding_dimension != expected_dimension:
                msg = (
                    f"Record at index {idx} has embedding_dimension "
                    f"{rec.embedding_dimension}, expected {expected_dimension}"
                )
                warnings.warn(msg)
                raise VectorStoreValidationError(msg)

    def _validate_vector(
        self,
        vector: list[float],
        expected_dimension: int,
        index: int,
    ) -> None:
        if not vector:
            msg = f"Vector at index {index} is empty"
            warnings.warn(msg)
            raise VectorStoreValidationError(msg)

        if len(vector) != expected_dimension:
            msg = (
                f"Vector at index {index} has dimension {len(vector)}, "
                f"expected {expected_dimension}"
            )
            warnings.warn(msg)
            raise VectorStoreValidationError(msg)

        for i, val in enumerate(vector):
            if math.isnan(val):
                msg = f"Vector at index {index} contains NaN at position {i}"
                warnings.warn(msg)
                raise VectorStoreValidationError(msg)
            if math.isinf(val):
                msg = f"Vector at index {index} contains Inf at position {i}"
                warnings.warn(msg)
                raise VectorStoreValidationError(msg)
