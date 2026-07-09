import math
import warnings

from app.services.embedding.models import EmbeddingInput


class EmbeddingValidationError(Exception):
    pass


class EmbeddingValidator:
    def validate_query_vector(
        self,
        vector: list[float],
        expected_dimension: int,
    ) -> None:
        self._validate_vector(vector, expected_dimension, 0)

    def validate_batch(
        self,
        vectors: list[list[float]],
        inputs: list[EmbeddingInput],
        expected_dimension: int,
    ) -> None:
        if len(vectors) != len(inputs):
            msg = (
                f"Vector count ({len(vectors)}) does not match "
                f"input count ({len(inputs)})"
            )
            warnings.warn(msg)
            raise EmbeddingValidationError(msg)

        for idx, (vector, inp) in enumerate(zip(vectors, inputs)):
            self._validate_vector(vector, expected_dimension, idx)

        for idx, inp in enumerate(inputs):
            if not inp.embedding_text.strip():
                msg = f"Input at index {idx} has empty embedding_text"
                warnings.warn(msg)
                raise EmbeddingValidationError(msg)
            if inp.chunk.metadata is None:
                msg = f"Input at index {idx} has no metadata"
                warnings.warn(msg)
                raise EmbeddingValidationError(msg)

    def _validate_vector(
        self, vector: list[float], expected_dimension: int, index: int
    ) -> None:
        if not vector:
            msg = f"Vector at index {index} is empty"
            warnings.warn(msg)
            raise EmbeddingValidationError(msg)

        if len(vector) != expected_dimension:
            msg = (
                f"Vector at index {index} has dimension {len(vector)}, "
                f"expected {expected_dimension}"
            )
            warnings.warn(msg)
            raise EmbeddingValidationError(msg)

        for i, val in enumerate(vector):
            if math.isnan(val):
                msg = f"Vector at index {index} contains NaN at position {i}"
                warnings.warn(msg)
                raise EmbeddingValidationError(msg)
            if math.isinf(val):
                msg = f"Vector at index {index} contains Inf at position {i}"
                warnings.warn(msg)
                raise EmbeddingValidationError(msg)
