from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.chunk import ContentType, StructuredUnit, UnitType
from app.schemas.document import Document, DocumentType
from app.services.chunking.hashers import stable_hash
from app.services.chunking.tokenizers import TokenCounter


@dataclass(frozen=True)
class _Line:
    text: str
    start: int
    end: int


class StructureParser:
    parser_version = "structure_parser_v1"

    def __init__(self, token_counter: TokenCounter | None = None) -> None:
        self.token_counter = token_counter or TokenCounter()

    def parse(self, document: Document) -> list[StructuredUnit]:
        lines = self._lines_with_offsets(document.text)
        units: list[StructuredUnit] = []
        header_path: list[str] = []
        source_id = stable_hash(document.metadata.user_id, document.metadata.source)
        index = 0
        i = 0

        while i < len(lines):
            line = lines[i]
            base_content_type = self._detect_document_region(document, line.text, index)

            if document.metadata.document_type == DocumentType.markdown and line.text.startswith("```"):
                block_lines = [line]
                i += 1
                while i < len(lines):
                    block_lines.append(lines[i])
                    if lines[i].text.startswith("```"):
                        i += 1
                        break
                    i += 1
                unit_text = "\n".join(item.text for item in block_lines)
                units.append(
                    self._unit(
                        document,
                        source_id,
                        unit_text,
                        UnitType.code,
                        index,
                        block_lines,
                        header_path,
                        ContentType.code,
                    )
                )
                index += 1
                continue

            if self._is_table_line(line.text):
                block_lines = [line]
                i += 1
                while i < len(lines) and self._is_table_line(lines[i].text):
                    block_lines.append(lines[i])
                    i += 1
                unit_text = "\n".join(item.text for item in block_lines)
                units.append(
                    self._unit(
                        document,
                        source_id,
                        unit_text,
                        UnitType.table,
                        index,
                        block_lines,
                        header_path,
                        ContentType.table,
                    )
                )
                index += 1
                continue

            if self._is_list_item(line.text):
                units.append(
                    self._unit(
                        document,
                        source_id,
                        line.text,
                        UnitType.list_item,
                        index,
                        [line],
                        header_path,
                        base_content_type,
                    )
                )
                index += 1
                i += 1
                continue

            heading = self._detect_heading(line.text, document.metadata.document_type)
            if heading is not None:
                level, title = heading
                header_path = self._update_header_path(header_path, level, title)
                units.append(
                    self._unit(
                        document,
                        source_id,
                        line.text,
                        UnitType.heading,
                        index,
                        [line],
                        header_path,
                        base_content_type
                        if base_content_type in {ContentType.cover, ContentType.toc, ContentType.reference}
                        else ContentType.heading,
                    )
                )
                index += 1
                i += 1
                continue

            units.append(
                self._unit(
                    document,
                    source_id,
                    line.text,
                    self._default_unit_type(document),
                    index,
                    [line],
                    header_path,
                    base_content_type,
                )
            )
            index += 1
            i += 1

        return units

    def _unit(
        self,
        document: Document,
        source_id: str,
        text: str,
        unit_type: UnitType,
        index: int,
        lines: list[_Line],
        header_path: list[str],
        content_type: ContentType,
    ) -> StructuredUnit:
        page = document.metadata.page_number
        section_title = header_path[-1] if header_path else None
        return StructuredUnit(
            unit_id=stable_hash(document.metadata.document_id, index, unit_type, text[:1024]),
            document_id=document.metadata.document_id,
            source_id=source_id,
            text=text,
            unit_type=unit_type,
            unit_index=index,
            token_count=self.token_counter.count(text),
            char_start=lines[0].start if lines else None,
            char_end=lines[-1].end if lines else None,
            page_start=page,
            page_end=page,
            section_title=section_title,
            header_path=list(header_path),
            content_type=content_type,
        )

    def _lines_with_offsets(self, text: str) -> list[_Line]:
        lines: list[_Line] = []
        cursor = 0
        for raw_line in text.split("\n"):
            start = cursor
            end = start + len(raw_line)
            stripped = raw_line.strip()
            if stripped:
                leading_ws = len(raw_line) - len(raw_line.lstrip())
                trailing_ws = len(raw_line) - len(raw_line.rstrip())
                lines.append(_Line(stripped, start + leading_ws, end - trailing_ws))
            cursor = end + 1
        return lines

    def _detect_heading(self, text: str, document_type: DocumentType) -> tuple[int, str] | None:
        if self._looks_like_formula(text):
            return None

        if document_type == DocumentType.markdown:
            markdown_match = re.match(r"^(#{1,6})\s+(.+)$", text)
            if markdown_match:
                return len(markdown_match.group(1)), markdown_match.group(2).strip()

        numbered_match = re.match(r"^(\d+(?:\.\d+){0,5})\.?\s+(.{3,120})$", text)
        if numbered_match:
            if "." not in numbered_match.group(1) and document_type != DocumentType.markdown:
                return None
            level = numbered_match.group(1).count(".") + 1
            return min(level, 6), text.strip()

        if 8 <= len(text) <= 120 and text.upper() == text and re.search(r"[A-ZÀ-Ỵ]", text):
            return 1, text.strip()

        return None

    def _update_header_path(self, header_path: list[str], level: int, title: str) -> list[str]:
        next_path = header_path[: max(0, level - 1)]
        next_path.append(title)
        return next_path

    def _is_table_line(self, text: str) -> bool:
        return text.count("|") >= 2

    def _is_list_item(self, text: str) -> bool:
        return bool(re.match(r"^(\-|\*|•|\d+\.)\s+", text))

    def _default_unit_type(self, document: Document) -> UnitType:
        if document.metadata.document_type == DocumentType.image:
            return UnitType.ocr_block
        return UnitType.paragraph

    def _detect_document_region(
        self,
        document: Document,
        text: str,
        unit_index: int,
    ) -> ContentType:
        lowered = text.casefold()

        if document.metadata.document_type == DocumentType.image:
            return ContentType.ocr
        if "mục lục" in lowered or "table of contents" in lowered:
            return ContentType.toc
        if "danh sách hình" in lowered or "danh sách bảng" in lowered:
            return ContentType.toc
        if "tài liệu tham khảo" in lowered or lowered.strip() in {"references", "reference"}:
            return ContentType.reference
        if (
            document.metadata.page_number == 1
            and unit_index <= 8
            and document.metadata.document_type in {DocumentType.pdf, DocumentType.docx}
        ):
            return ContentType.cover

        return ContentType.body

    def _looks_like_formula(self, text: str) -> bool:
        if "=" in text:
            return True

        formula_symbols = set("=∑√≈≤≥∞∫∆π±×÷^_{}[]()")
        operator_symbols = set("+-*/^=∑√≈≤≥∞")
        non_space = [char for char in text if not char.isspace()]
        if not non_space:
            return False

        symbol_count = sum(1 for char in non_space if char in formula_symbols)
        operator_count = sum(1 for char in non_space if char in operator_symbols)
        digit_count = sum(1 for char in non_space if char.isdigit())
        alpha_count = sum(1 for char in non_space if char.isalpha())

        symbol_ratio = symbol_count / len(non_space)
        digit_symbol_ratio = (digit_count + symbol_count) / len(non_space)

        if operator_count >= 2 and digit_count >= 1:
            return True
        if symbol_ratio >= 0.18 and digit_count >= 1:
            return True
        if digit_symbol_ratio >= 0.55 and alpha_count <= 4:
            return True
        if re.search(r"\b[A-Za-zÀ-ỹ]\s*=\s*", text):
            return True

        return False
