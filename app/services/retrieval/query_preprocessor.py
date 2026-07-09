from __future__ import annotations

import re


class QueryPreprocessor:
    def __init__(
        self,
        *,
        lowercase: bool = False,
        remove_noisy_punctuation: bool = True,
    ) -> None:
        self.lowercase = lowercase
        self.remove_noisy_punctuation = remove_noisy_punctuation

    def normalize(self, query: str) -> str:
        text = query.strip()
        if not text:
            raise ValueError("query must not be empty")

        text = re.sub(r"\s+", " ", text, flags=re.UNICODE)
        text = re.sub(r"\s+([?.!,;:])", r"\1", text, flags=re.UNICODE)

        if self.remove_noisy_punctuation:
            text = self._normalize_punctuation(text)

        if self.lowercase:
            text = text.casefold()

        if not text.strip():
            raise ValueError("query must not be empty")

        return text

    def _normalize_punctuation(self, text: str) -> str:
        text = re.sub(r"\?{2,}", "?", text)
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"\.{4,}", "...", text)
        text = re.sub(r"([?!.,;:])\s*([?!.,;:])+", r"\1", text)
        return text.strip()
