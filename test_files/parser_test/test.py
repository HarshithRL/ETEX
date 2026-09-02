#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root so `shared.artifacts` resolves when this file is run as a script.
# Usage (from ai_application, with venv):
#   .\.venv\Scripts\python.exe test_files\parser_test\test.py "C:\path\to\file.pdf" classify
#   .\.venv\Scripts\python.exe test_files\parser_test\test.py "C:\path\to\file.pdf" parse
# Markdown is written to test_files/parser_test/<stem>.md (override with --md-out)
#   .\.venv\Scripts\python.exe test_files\parser_test\test.py "C:\path\to\file.pdf" parse --plain
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.artifacts import ArtifactHandler, ParseOptions
from shared.artifacts.exceptions import ArtifactError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ArtifactHandler classify / parse against a file."
    )
    parser.add_argument("path", help="Path to the artifact (pdf, pptx, docx, xlsx)")
    parser.add_argument(
        "action",
        choices=("classify", "parse"),
        help="classify = detect type (pdf|ppt|excel|word); parse = extract structured content",
    )
    parser.add_argument(
        "--type",
        dest="artifact_type",
        choices=("pdf", "ppt", "excel", "word"),
        default=None,
        help="Optional type for parse. If omitted, classify() runs first.",
    )
    parser.add_argument("--password", default=None, help="Password for encrypted PDFs")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit PDF pages / PPT slides extracted",
    )
    parser.add_argument(
        "--include-images",
        action="store_true",
        help="Include image placeholder blocks (pptx)",
    )
    parser.add_argument(
        "--include-hidden-sheets",
        action="store_true",
        help="Include hidden Excel sheets",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="For PDF parse: enable OCR on scanned/design pages (ParseOptions.use_ocr)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="For parse: print plain text instead of JSON",
    )
    parser.add_argument(
        "--md-out",
        default=None,
        help="Write parse Markdown to this path. Default: test_files/parser_test/<stem>.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.path).expanduser().resolve()
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    handler = ArtifactHandler()
    try:
        if args.action == "classify":
            kind = handler.classify(path)
            output = {"path": str(path), "action": "classify", "artifact_type": kind.value}
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        document = handler.parse(
            path,
            args.artifact_type,
            options=ParseOptions(
                password=args.password,
                include_images=args.include_images,
                include_hidden_sheets=args.include_hidden_sheets,
                max_pages=args.max_pages,
                use_ocr=args.ocr,
            ),
        )
        if args.plain:
            print(document.plain_text())
        else:
            print(json.dumps(document.to_dict(), indent=2, ensure_ascii=False, default=str))

        md_path = Path(args.md_out).expanduser() if args.md_out else Path(__file__).resolve().parent / f"{path.stem}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = document.md_text()
        if markdown and not markdown.endswith("\n"):
            markdown += "\n"
        md_path.write_text(markdown, encoding="utf-8")
        print(f"wrote markdown: {md_path}", file=sys.stderr)
        return 0
    except ArtifactError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())