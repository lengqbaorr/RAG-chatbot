from app.schemas.chunk import DocumentChunk
from app.services.chunking.hashers import stable_hash


class ChunkValidationError(ValueError):
    pass


class ChunkValidator:
    def __init__(self, *, max_tokens: int, allow_overflow_tokens: int = 32) -> None:
        self.max_tokens = max_tokens
        self.allow_overflow_tokens = allow_overflow_tokens

    def validate(self, chunks: list[DocumentChunk]) -> None:
        seen_ids: set[str] = set()
        for expected_index, chunk in enumerate(chunks):
            if chunk.chunk_index != expected_index:
                raise ChunkValidationError("chunk_index must be contiguous per document")
            if not chunk.text.strip():
                raise ChunkValidationError("chunk text cannot be empty")
            if chunk.chunk_id in seen_ids:
                raise ChunkValidationError(f"duplicate chunk_id: {chunk.chunk_id}")
            if chunk.content_hash != stable_hash(chunk.text):
                raise ChunkValidationError("content_hash does not match chunk text")
            if chunk.token_count > self.max_tokens + self.allow_overflow_tokens:
                raise ChunkValidationError(
                    f"chunk has {chunk.token_count} tokens, max allowed is "
                    f"{self.max_tokens + self.allow_overflow_tokens}"
                )
            seen_ids.add(chunk.chunk_id)
