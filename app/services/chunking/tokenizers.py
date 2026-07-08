from __future__ import annotations

import re


class TokenCounter:
    def __init__(self, encoding_name: str = "simple") -> None:
        self.encoding_name = encoding_name
        self._encoding = None

    @property
    def encoding(self):
        if self.encoding_name in {"simple", "approx"}:
            return None
        if self._encoding is None:
            try:
                import tiktoken

                self._encoding = tiktoken.get_encoding(self.encoding_name)
            except Exception:
                self._encoding = None
        return self._encoding

    def count(self, text: str) -> int:
        if not text:
            return 0
        encoding = self.encoding
        if encoding is not None:
            return len(encoding.encode(text))
        return len(self._simple_tokens(text))

    def split_by_tokens(
        self,
        text: str,
        *,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        encoding = self.encoding
        if encoding is None:
            return self._split_simple_tokens(
                text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

        tokens = encoding.encode(text)
        if len(tokens) <= chunk_size:
            return [text]

        step = max(1, chunk_size - chunk_overlap)
        chunks: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            decoded = encoding.decode(tokens[start:end]).strip()
            if decoded:
                chunks.append(decoded)
            if end >= len(tokens):
                break
            start += step

        return chunks

    def _simple_tokens(self, text: str) -> list[str]:
        return re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)

    def _split_simple_tokens(
        self,
        text: str,
        *,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        parts = re.findall(r"\S+\s*", text, flags=re.UNICODE)
        if len(parts) <= chunk_size:
            return [text]

        step = max(1, chunk_size - chunk_overlap)
        chunks: list[str] = []
        start = 0
        while start < len(parts):
            end = min(start + chunk_size, len(parts))
            chunk = "".join(parts[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(parts):
                break
            start += step
        return chunks
