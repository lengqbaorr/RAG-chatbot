import re
import unicodedata


class TextNormalizer:
    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", normalized)
        normalized = re.sub(r"(?<=\w)-\n(?=\w)", "", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        lines = [line.strip() for line in normalized.split("\n")]
        return "\n".join(line for line in lines if line).strip()
