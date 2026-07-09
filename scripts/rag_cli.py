from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = "Test.pdf"
DEFAULT_QUERY = "Vector Space Model là gì?"
DEFAULT_DATASET = "data/evaluation/test_data.jsonl"
DEFAULT_EVAL_COLLECTION = "eval_test_pdf_bge_m3_1024"
DEFAULT_EVAL_PERSIST = "./data/chroma_eval"
DEFAULT_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def run_python(args: list[str], *, title: str) -> None:
    print()
    print("=" * 80, flush=True)
    print(title, flush=True)
    print("=" * 80, flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
    subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


def run_external(args: list[str], *, title: str) -> None:
    print()
    print("=" * 80, flush=True)
    print(title, flush=True)
    print("=" * 80, flush=True)
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def add_common_doc_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--local-files-only", action="store_true")


def add_retrieval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--fetch-k", type=int, default=10)
    parser.add_argument("--min-score", type=float, default=0.70)


def cmd_preload(args: argparse.Namespace) -> None:
    run_all = args.all or not args.embedding and not args.reranker
    if args.embedding or run_all:
        command = ["scripts/preload_embedding_model.py"]
        if args.local_files_only:
            command.append("--local-files-only")
        run_python(command, title="PRELOAD EMBEDDING")

    if args.reranker or run_all:
        command = [
            "scripts/preload_reranker_model.py",
            "--model-name",
            args.reranker_model,
        ]
        if args.local_files_only:
            command.append("--local-files-only")
        run_python(command, title="PRELOAD RERANKER")


def cmd_inspect(args: argparse.Namespace) -> None:
    chunk_command = [
        "scripts/print_chunks.py",
        args.source,
        "--chunk-size",
        str(args.chunk_size),
        "--chunk-overlap",
        str(args.chunk_overlap),
        "--limit",
        str(args.limit),
    ]
    if args.parents:
        chunk_command.append("--parents")
    if args.level != "all":
        chunk_command.extend(["--level", args.level])
    if args.all_chunks:
        chunk_command.append("--all")
    run_python(chunk_command, title="INSPECT CHUNKS")

    if args.embedding:
        embedding_command = [
            "scripts/preload_embedding_model.py",
            "--warmup-text",
            args.query,
        ]
        if args.local_files_only:
            embedding_command.append("--local-files-only")
        run_python(embedding_command, title="INSPECT EMBEDDING")


def cmd_demo(args: argparse.Namespace) -> None:
    if args.mode == "all":
        print(
            "Note: --all runs mock demos plus real retriever and real RAG. "
            "Use --real for one real end-to-end run.",
            flush=True,
        )

    run_mock = args.mode in ("mock", "all")
    run_real_retriever = args.mode in ("retriever", "all")
    run_real_rag = args.mode in ("rag", "all")

    if run_mock:
        run_python(
            [
                "scripts/demo_retriever.py",
                "--query",
                args.query,
                "--top-k",
                str(args.top_k),
                "--fetch-k",
                str(args.fetch_k),
                "--min-score",
                str(args.min_score),
            ],
            title="DEMO RETRIEVER MOCK",
        )
        run_python(["scripts/demo_rag.py", "--query", args.query], title="DEMO RAG MOCK")

    if run_real_retriever or run_real_rag:
        retriever_command = [
            "scripts/demo_retriever.py",
            "--real",
            "--source",
            args.source,
            "--query",
            args.query,
            "--top-k",
            str(args.top_k),
            "--fetch-k",
            str(args.fetch_k),
            "--min-score",
            str(args.min_score),
        ]
        rag_command = [
            "scripts/demo_rag_real.py",
            "--source",
            args.source,
            "--query",
            args.query,
            "--provider",
            args.provider,
            "--top-k",
            str(args.top_k),
            "--fetch-k",
            str(args.fetch_k),
            "--min-score",
            str(args.min_score),
            "--max-context-tokens",
            str(args.max_context_tokens),
            "--max-tokens",
            str(args.max_tokens),
            "--temperature",
            str(args.temperature),
        ]
        if args.model:
            rag_command.extend(["--model", args.model])
        if args.local_files_only:
            retriever_command.append("--local-files-only")
            rag_command.append("--local-files-only")
        if run_real_retriever:
            run_python(retriever_command, title="DEMO RETRIEVER REAL")
        if run_real_rag:
            run_python(rag_command, title="DEMO RAG REAL")


def cmd_eval(args: argparse.Namespace) -> None:
    if args.index:
        index_command = [
            "scripts/index_eval_document.py",
            args.source,
            "--collection",
            args.collection,
            "--persist-directory",
            args.persist_directory,
            "--chunk-size",
            str(args.chunk_size),
            "--chunk-overlap",
            str(args.chunk_overlap),
            "--parent-size",
            str(args.parent_size),
        ]
        if args.no_cache:
            index_command.append("--no-cache")
        if args.local_files_only:
            index_command.append("--local-files-only")
        run_python(index_command, title="INDEX EVAL DOCUMENT")

    eval_command = [
        "scripts/run_retrieval_experiments.py",
        "--dataset",
        args.dataset,
        "--collection",
        args.collection,
        "--persist-directory",
        args.persist_directory,
        "--output",
        args.output,
    ]
    if args.no_cache:
        eval_command.append("--no-cache")
    if args.local_files_only:
        eval_command.append("--local-files-only")
    if args.with_reranker:
        eval_command.extend(["--with-reranker", "--reranker-model", args.reranker_model])
    run_python(eval_command, title="RUN RETRIEVAL EVALUATION")


def cmd_api(args: argparse.Namespace) -> None:
    run_python(
        [
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        title="RUN API",
    )


def cmd_test(args: argparse.Namespace) -> None:
    command = ["-m", "pytest"]
    if args.path:
        command.append(args.path)
    if args.quiet:
        command.append("-q")
    run_python(command, title="RUN TESTS")


def cmd_ports(args: argparse.Namespace) -> None:
    run_external(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"netstat -ano | Select-String ':{args.port}'",
        ],
        title=f"PORTS: {args.port}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified CLI for common RAG chatbot commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preload = subparsers.add_parser("preload", help="Preload embedding and reranker models.")
    preload.add_argument("--all", action="store_true")
    preload.add_argument("--embedding", action="store_true")
    preload.add_argument("--reranker", action="store_true")
    preload.add_argument("--reranker-model", default=DEFAULT_RERANKER)
    preload.add_argument("--local-files-only", action="store_true")
    preload.set_defaults(func=cmd_preload)

    inspect_cmd = subparsers.add_parser("inspect", help="Print chunks and optionally embedding warmup.")
    add_common_doc_args(inspect_cmd)
    inspect_cmd.add_argument("--chunk-size", type=int, default=450)
    inspect_cmd.add_argument("--chunk-overlap", type=int, default=60)
    inspect_cmd.add_argument("--parents", action="store_true")
    inspect_cmd.add_argument("--level", choices=("all", "child", "parent"), default="all")
    inspect_cmd.add_argument("--limit", type=int, default=3)
    inspect_cmd.add_argument("--all-chunks", action="store_true")
    inspect_cmd.add_argument("--embedding", action="store_true", default=True)
    inspect_cmd.set_defaults(func=cmd_inspect)

    demo = subparsers.add_parser("demo", help="Run demo suite.")
    add_common_doc_args(demo)
    add_retrieval_args(demo)
    demo.add_argument("--mode", choices=("mock", "retriever", "rag", "all"), default="mock")
    demo.add_argument("--all", action="store_const", const="all", dest="mode")
    demo.add_argument("--real", action="store_const", const="rag", dest="mode")
    demo.add_argument("--provider", choices=("gemini", "openrouter", "ollama"), default="gemini")
    demo.add_argument("--model", default=None)
    demo.add_argument("--max-context-tokens", type=int, default=3000)
    demo.add_argument("--max-tokens", type=int, default=1024)
    demo.add_argument("--temperature", type=float, default=0.2)
    demo.set_defaults(func=cmd_demo)

    eval_cmd = subparsers.add_parser("eval", help="Index eval document and run retrieval experiments.")
    eval_cmd.add_argument("--source", default=DEFAULT_SOURCE)
    eval_cmd.add_argument("--dataset", default=DEFAULT_DATASET)
    eval_cmd.add_argument("--collection", default=DEFAULT_EVAL_COLLECTION)
    eval_cmd.add_argument("--persist-directory", default=DEFAULT_EVAL_PERSIST)
    eval_cmd.add_argument("--index", action="store_true")
    eval_cmd.add_argument("--chunk-size", type=int, default=450)
    eval_cmd.add_argument("--chunk-overlap", type=int, default=60)
    eval_cmd.add_argument("--parent-size", type=int, default=1600)
    eval_cmd.add_argument("--no-cache", action="store_true")
    eval_cmd.add_argument("--local-files-only", action="store_true")
    eval_cmd.add_argument("--with-reranker", action="store_true")
    eval_cmd.add_argument("--reranker-model", default=DEFAULT_RERANKER)
    eval_cmd.add_argument("--output", choices=("markdown", "csv", "json"), default="markdown")
    eval_cmd.set_defaults(func=cmd_eval)

    api = subparsers.add_parser("api", help="Run FastAPI server.")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)
    api.set_defaults(func=cmd_api)

    test = subparsers.add_parser("test", help="Run pytest.")
    test.add_argument("path", nargs="?")
    test.add_argument("-q", "--quiet", action="store_true")
    test.set_defaults(func=cmd_test)

    ports = subparsers.add_parser("ports", help="Show netstat output.")
    ports.add_argument("--port", type=int, default=8000)
    ports.set_defaults(func=cmd_ports)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
