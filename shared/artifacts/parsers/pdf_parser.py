from __future__ import annotations

from pathlib import Path

import pymupdf

from ..blocks import make_content_block
from ..exceptions import ArtifactParseError, CorruptArtifact, EncryptedArtifact
from ..heading_stack import HeadingStack
from ..ids import file_artifact_id
from ..models import (
    COORD_PDF_POINTS,
    ArtifactDocument,
    ArtifactMetadata,
    ArtifactType,
    BlockType,
    ContentBlock,
    MIME_BY_TYPE,
    OutlineItem,
    PageInfo,
    ParseOptions,
    SourceLocation,
)
from .pdf_chrome import PdfHeaderFooterDetector
from .pdf_geometry import overlaps_any, round_bbox
from .pdf_headings import apply_heading_paths, lines_to_blocks, merge_cover_titles
from .pdf_layout import PdfLayoutExtractor, PdfPageClassifier, PdfTextNormalizer
from .pdf_ocr import PdfOcrFallback
from .pdf_tables import PdfTableExtractor, table_to_text
from .pdf_visuals import extract_visuals


class PdfParser:
    kind = ArtifactType.PDF

    def parse(self, path: Path, options: ParseOptions) -> ArtifactDocument:
        try:
            document = pymupdf.open(str(path))
        except Exception as exc:
            raise CorruptArtifact(f"Failed to open PDF: {path.name}") from exc

        encrypted = bool(document.is_encrypted)
        try:
            if encrypted:
                if not document.authenticate(options.password or ""):
                    raise EncryptedArtifact(
                        f"PDF is encrypted and requires a valid password: {path.name}"
                    )
            page_count = document.page_count
            selected = list(document)
            if options.max_pages is not None:
                selected = selected[: options.max_pages]
            meta = document.metadata or {}
            title = _meta_str(meta.get("title"))
            author = _meta_str(meta.get("author"))
            created = _meta_str(meta.get("creationDate"))
            modified = _meta_str(meta.get("modDate"))

            chrome = PdfHeaderFooterDetector().detect(selected)
            classifier = PdfPageClassifier()
            extractor = PdfLayoutExtractor()
            tables = PdfTableExtractor()
            ocr = PdfOcrFallback()
            normalizer = PdfTextNormalizer()
            stack = HeadingStack()

            blocks: list[ContentBlock] = []
            pages: list[PageInfo] = []
            warnings: list[str] = []
            index = 0

            for page_index, page in enumerate(selected):
                page_no = page.number + 1
                page_width = float(page.rect.width or 0)
                page_height = float(page.rect.height or 0)
                page_kind = classifier.classify(page)
                pages.append(
                    PageInfo(
                        page=page_no,
                        width=page_width,
                        height=page_height,
                        rotation=int(page.rotation or 0),
                        kind=page_kind,
                    )
                )

                page_tables: list[tuple[list[list[str]], tuple[float, float, float, float], str]] = []
                if options.include_tables and page_kind in {"table", "digital", "mixed", "design"}:
                    page_tables = tables.extract(page, path, page_index, page_kind, options.password)

                table_boxes = [bbox for _, bbox, _ in page_tables]
                chrome_detector = PdfHeaderFooterDetector()
                lines = [
                    line
                    for line in extractor.lines(page, page_no)
                    if not chrome_detector.is_chrome(
                        line.text, line.bbox, page_height or 1, chrome
                    )
                    and not overlaps_any(line.bbox, table_boxes)
                ]
                lines = merge_cover_titles(lines, page_kind)

                page_blocks: list[ContentBlock] = []
                for table_i, (matrix, bbox, engine) in enumerate(page_tables):
                    index += 1
                    page_blocks.append(
                        make_content_block(
                            seq_id=f"pdf-{index:04d}",
                            block_type=BlockType.TABLE,
                            text=table_to_text(matrix),
                            table=matrix,
                            location=SourceLocation(
                                page=page_no,
                                bbox=round_bbox(bbox),
                                page_width=page_width,
                                page_height=page_height,
                                table_index=table_i,
                            ),
                            extra={"engine": engine, "page_kind": page_kind},
                        )
                    )

                index, visual_blocks = extract_visuals(
                    page, lines, page_kind, page_no, table_boxes, index
                )
                page_blocks.extend(visual_blocks)

                index, text_blocks = lines_to_blocks(
                    lines, page_kind, page_no, index, page_width, page_height
                )
                page_blocks.extend(text_blocks)

                page_has_text = any(
                    block.type not in {BlockType.IMAGE, BlockType.CHART} for block in page_blocks
                )
                if not page_has_text and page_kind in {"scanned", "design"}:
                    if options.use_ocr:
                        ocr_text = ocr.extract(page, warnings, page_no)
                        if ocr_text:
                            index, ocr_block = ocr.as_block(
                                ocr_text, page_no, page_width, page_height, page_kind, index
                            )
                            page_blocks.append(ocr_block)
                            page_has_text = True
                    if not page_has_text:
                        fallback = normalizer.normalize(page.get_text("text") or "")
                        if fallback:
                            index += 1
                            page_blocks.append(
                                make_content_block(
                                    seq_id=f"pdf-{index:04d}",
                                    block_type=BlockType.TEXT,
                                    text=fallback,
                                    location=SourceLocation(
                                        page=page_no,
                                        page_width=page_width,
                                        page_height=page_height,
                                    ),
                                    extra={"engine": "pymupdf.text", "page_kind": page_kind},
                                )
                            )
                            page_has_text = True
                    if not page_has_text:
                        warnings.append(
                            f"Page {page_no} is a {page_kind} page with little extractable text."
                        )

                page_blocks.sort(key=_reading_key)
                apply_heading_paths(page_blocks, stack)
                blocks.extend(page_blocks)
        except EncryptedArtifact:
            raise
        except ArtifactParseError:
            raise
        except Exception as exc:
            raise ArtifactParseError(f"Failed to extract PDF {path.name}: {exc}") from exc
        finally:
            document.close()

        if not blocks:
            warnings.append("No extractable text or tables found (possible scanned PDF).")

        outline = [
            OutlineItem(
                title=block.text.split("\n", 1)[0].strip(),
                page=block.location.page,
                level=block.level or 2,
                block_id=block.block_id,
            )
            for block in blocks
            if block.type == BlockType.HEADING
        ]

        return ArtifactDocument(
            source=str(path),
            artifact_type=ArtifactType.PDF,
            artifact_id=file_artifact_id(path),
            coord_system=COORD_PDF_POINTS,
            metadata=ArtifactMetadata(
                filename=path.name,
                artifact_type=ArtifactType.PDF,
                mime_type=MIME_BY_TYPE[ArtifactType.PDF],
                title=title,
                author=author,
                created=created,
                modified=modified,
                page_count=page_count,
                encrypted=encrypted,
            ),
            pages=pages,
            outline=outline,
            blocks=blocks,
            warnings=warnings,
        )


def _reading_key(block: ContentBlock) -> tuple[float, float]:
    bbox = block.location.bbox
    if bbox is None:
        return (10_000.0, 0.0)
    return (bbox[1], bbox[0])


def _meta_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None



