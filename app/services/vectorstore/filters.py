import warnings

SUPPORTED_FIELDS = frozenset({
    "document_id",
    "source_id",
    "source_name",
    "source_type",
    "content_type",
    "chunk_level",
    "parent_id",
    "page_start",
    "page_end",
    "embedding_model",
    "embedding_version",
    "header_path_text",
    "language",
})

SUPPORTED_OPERATORS = frozenset({"$eq", "$ne", "$in", "$gte", "$lte"})


class FilterBuilderError(Exception):
    pass


class ChromaFilterBuilder:
    @staticmethod
    def build(filters: dict | None) -> dict | None:
        if not filters:
            return None

        conditions: list[dict] = []

        for field, value in filters.items():
            if field not in SUPPORTED_FIELDS:
                warnings.warn(f"Unsupported filter field '{field}', skipping")
                continue

            if isinstance(value, dict):
                for op, operand in value.items():
                    if op not in SUPPORTED_OPERATORS:
                        msg = f"Unsupported operator '{op}' for field '{field}'"
                        warnings.warn(msg)
                        raise FilterBuilderError(msg)
                    conditions.append({field: {op: operand}})
            else:
                conditions.append({field: {"$eq": value}})

        if len(conditions) == 0:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}
