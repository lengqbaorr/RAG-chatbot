import pytest

from app.services.vectorstore.filters import (
    ChromaFilterBuilder,
    FilterBuilderError,
)


class TestChromaFilterBuilder:
    def test_none_returns_none(self):
        assert ChromaFilterBuilder.build(None) is None

    def test_empty_dict_returns_none(self):
        assert ChromaFilterBuilder.build({}) is None

    def test_simple_eq_filter(self):
        result = ChromaFilterBuilder.build({"content_type": "body"})
        assert result == {"content_type": {"$eq": "body"}}

    def test_explicit_eq(self):
        result = ChromaFilterBuilder.build({"chunk_level": {"$eq": "child"}})
        assert result == {"chunk_level": {"$eq": "child"}}

    def test_ne_filter(self):
        result = ChromaFilterBuilder.build({"chunk_level": {"$ne": "parent"}})
        assert result == {"chunk_level": {"$ne": "parent"}}

    def test_in_filter(self):
        result = ChromaFilterBuilder.build({"content_type": {"$in": ["body", "heading"]}})
        assert result == {"content_type": {"$in": ["body", "heading"]}}

    def test_gte_filter(self):
        result = ChromaFilterBuilder.build({"page_start": {"$gte": 1}})
        assert result == {"page_start": {"$gte": 1}}

    def test_lte_filter(self):
        result = ChromaFilterBuilder.build({"page_end": {"$lte": 10}})
        assert result == {"page_end": {"$lte": 10}}

    def test_multiple_filters_combine_with_and(self):
        result = ChromaFilterBuilder.build({
            "content_type": "body",
            "chunk_level": "child",
        })
        assert result == {
            "$and": [
                {"content_type": {"$eq": "body"}},
                {"chunk_level": {"$eq": "child"}},
            ]
        }

    def test_mixed_operators(self):
        result = ChromaFilterBuilder.build({
            "content_type": "body",
            "page_start": {"$gte": 1, "$lte": 10},
        })
        assert result == {
            "$and": [
                {"content_type": {"$eq": "body"}},
                {"page_start": {"$gte": 1}},
                {"page_start": {"$lte": 10}},
            ]
        }

    def test_unsupported_field_skipped(self):
        result = ChromaFilterBuilder.build({"unsupported_field": "value"})
        assert result is None

    def test_unsupported_operator_raises(self):
        with pytest.raises(FilterBuilderError):
            ChromaFilterBuilder.build({"page_start": {"$regex": "test"}})
