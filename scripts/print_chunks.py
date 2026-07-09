from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chunking import ChunkingConfig, ChunkQualityReporter, DocumentChunker
from app.services.ingestion import DocumentLoaderService, LoaderInput


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load a document and print generated chunks.")
    parser.add_argument(
        "source",
        nargs="?",
        default="Test.pdf",
        help="Path or URL to load. Defaults to the sample PDF in the project root.",
    )
    parser.add_argument("--chunk-size", type=int, default=450)
    parser.add_argument("--chunk-overlap", type=int, default=60)
    parser.add_argument("--parents", action="store_true", help="Also build parent chunks.")
    parser.add_argument("--parent-size", type=int, default=1600)
    parser.add_argument(
        "--level",
        choices=["all", "child", "parent"],
        default="all",
        help="Filter chunks by chunk level when printing.",
    )
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of chunks to print.")
    parser.add_argument("--all", action="store_true", help="Print all chunks.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source

    documents = DocumentLoaderService().load(LoaderInput(source=source))
    chunks = DocumentChunker(
        config=ChunkingConfig(
            chunk_size_tokens=args.chunk_size,
            chunk_overlap_tokens=args.chunk_overlap,
            build_parent_chunks=args.parents,
            parent_chunk_size_tokens=args.parent_size,
        )
    ).chunk_documents(documents)

    print(f"source: {source}")
    print(f"documents: {len(documents)}")
    report = ChunkQualityReporter().build(chunks)
    print("quality_report:")
    print(f"  total_chunks: {report.total_chunks}")
    print(f"  tokens: min={report.min_tokens} p50={report.p50_tokens} p90={report.p90_tokens} max={report.max_tokens} avg={report.avg_tokens}")
    print(f"  chunks_under_100: {report.chunks_under_100}")
    print(f"  chunks_over_900: {report.chunks_over_900}")
    print(f"  empty_chunks: {report.empty_chunks}")
    print(f"  duplicate_chunks: {report.duplicate_chunks}")
    print(f"  suspected_formula_headings: {report.suspected_formula_headings}")
    print(f"  retrieval_excluded_chunks: {report.retrieval_excluded_chunks}")
    print(f"  content_type_distribution: {report.content_type_distribution}")
    print(f"  chunk_level_distribution: {report.chunk_level_distribution}")
    print(f"  source_type_distribution: {report.source_type_distribution}")
    print("=" * 80)

    printable_chunks = [
        chunk for chunk in chunks if args.level == "all" or chunk.metadata.chunk_level == args.level
    ]
    chunks_to_print = printable_chunks if args.all else printable_chunks[: args.limit]
    for ordinal, chunk in enumerate(chunks_to_print):
        metadata = chunk.metadata
        print(f"ordinal: {ordinal}")
        print(f"chunk_index: {chunk.chunk_index}")
        print(f"chunk_id: {chunk.chunk_id}")
        print(f"tokens: {chunk.token_count}")
        print(f"source_name: {metadata.source_name}")
        print(f"source_type: {metadata.source_type}")
        print(f"content_type: {metadata.content_type}")
        print(f"retrieval_excluded: {metadata.retrieval_excluded}")
        print(f"language: {metadata.language}")
        print(f"chunk_level: {metadata.chunk_level}")
        print(f"page: {metadata.page_start}-{metadata.page_end}")
        print(f"section_title: {metadata.section_title}")
        print(f"header_path: {' > '.join(metadata.header_path)}")
        print(f"parser_version: {metadata.parser_version}")
        print(f"chunker_version: {metadata.chunker_version}")
        print("-" * 80)
        print(chunk.text)
        print("=" * 80)


if __name__ == "__main__":
    main()

