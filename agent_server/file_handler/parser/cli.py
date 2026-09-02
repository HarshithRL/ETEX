"""CLI: batch-convert documents to Markdown."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_server.file_handler.parser.router import (
    SUPPORTED_EXTENSIONS,
    DocumentParser,
)


def _output_path(source: Path, root: Path, out_dir: Path) -> Path:
    try:
        rel = source.relative_to(root)
    except ValueError:
        rel = Path(source.name)
    return out_dir / Path(str(rel) + ".md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent_server.file_handler.parser",
        description="Parse PDF/DOCX/XLSX/PPTX files to Markdown (Docling → native).",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="File or directory to parse",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for .md files (required for directory input)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recurse into subdirectories (default: true)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="Do not recurse into subdirectories",
    )
    parser.add_argument(
        "--native-only",
        action="store_true",
        help="Skip Docling; use native parsers only",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.input.expanduser().resolve()
    prefer_docling = not args.native_only
    parser = DocumentParser(prefer_docling=prefer_docling)

    if source.is_file():
        result = parser.parse_file(source)
        if args.out is not None:
            out_dir = args.out.expanduser().resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / (source.name + ".md")
            if result.ok:
                target.write_text(result.markdown, encoding="utf-8")
            print(
                f"{'[ok]' if result.ok else '[fail]'} {source.name} "
                f"engine={result.engine} chars={len(result.markdown)}"
                + (f" error={result.error}" if result.error else "")
                + (f" -> {target}" if result.ok else "")
            )
        else:
            if result.error:
                print(result.error, file=sys.stderr)
                return 1
            sys.stdout.write(result.markdown)
        return 0 if result.ok else 1

    if not source.is_dir():
        print(f"Not found: {source}", file=sys.stderr)
        return 1

    if args.out is None:
        print("--out is required when input is a directory", file=sys.stderr)
        return 2

    out_dir = args.out.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = parser.parse_dir(source, recursive=args.recursive)

    failed = 0
    for result in results:
        status = "ok" if result.ok else "fail"
        line = (
            f"[{status}] {result.source_path.relative_to(source)} "
            f"engine={result.engine} chars={len(result.markdown)}"
        )
        if result.error:
            line += f" error={result.error}"
            failed += 1
            print(line)
            continue
        target = _output_path(result.source_path, source, out_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.markdown, encoding="utf-8")
        print(f"{line} -> {target.relative_to(out_dir)}")

    skipped = sum(
        1
        for p in (source.rglob("*") if args.recursive else source.glob("*"))
        if p.is_file() and p.suffix.lower() not in SUPPORTED_EXTENSIONS
    )
    print(
        f"Done: {len(results) - failed} ok, {failed} failed, "
        f"{skipped} unsupported skipped"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
