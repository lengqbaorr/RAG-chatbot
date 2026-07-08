from app.schemas.chunk import DocumentChunk


class EmbeddingTextBuilder:
    def build(self, chunk: DocumentChunk) -> str:
        metadata = chunk.metadata
        source_name = metadata.source_name or "unknown"

        header_path = metadata.header_path
        if header_path:
            section = " > ".join(header_path)
        elif metadata.section_title:
            section = metadata.section_title
        else:
            section = ""

        lines: list[str] = []
        lines.append(f"Document: {source_name}")
        if section:
            lines.append(f"Section: {section}")
        lines.append("Content:")
        lines.append(chunk.text)

        return "\n".join(lines)
