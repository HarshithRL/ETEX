from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .classifier import ArtifactClassifier, LEGACY_OLE_HINT
from .exceptions import (
    ArtifactNotFound,
    ArtifactParseError,
    ArtifactPatchError,
    ArtifactWriteError,
    CorruptArtifact,
    EncryptedArtifact,
    UnsupportedArtifact,
)
from .models import ArtifactDocument, ArtifactType, ParseOptions, source_name
from .parsers.registry import LEGACY_EXTENSIONS, PARSEABLE_EXTENSIONS, parser_for
from .patch import apply_ops_to_spec, document_to_spec
from .spec import ArtifactSpec, PatchOp, WRITE_EXTENSIONS, coerce_ops, coerce_spec
from .writers.registry import writer_for


class ArtifactHandler:
    """Facade for artifact classification, parsing, create, and update.

    Agents emit a JSON ArtifactSpec and call create(spec). To edit a file,
    parse() it, then update(source, ops) with PatchOp dicts targeting block_id
    (or SourceLocation: paragraph_index / shape_id / cell_range / slide / sheet).
    Office XML (docx/pptx/xlsx) is patched in place; PDFs are regenerated from
    a spec derived from the parsed document. Unknown ops and missing targets
    raise ArtifactPatchError.
    """

    SUPPORTED_TYPES = (ArtifactType.PDF, ArtifactType.PPT, ArtifactType.EXCEL, ArtifactType.WORD)

    def __init__(self) -> None:
        self._classifier = ArtifactClassifier()

    def classify(
        self,
        source: str | Path | bytes,
        filename: str | None = None,
    ) -> ArtifactType:
        """Classify an artifact as pdf, ppt, excel, or word.

        Uses file extension first, then magic bytes / Open XML package parts
        when the extension is missing or disagrees with the file body.
        """
        return self._classifier.classify(source, filename=filename)

    def parse(
        self,
        source: str | Path | bytes,
        artifact_type: ArtifactType | str | None = None,
        *,
        filename: str | None = None,
        options: ParseOptions | None = None,
    ) -> ArtifactDocument:
        """Parse a file with the parser that matches its artifact type.

        If artifact_type is omitted, classify() is called first.
        """
        options = options or ParseOptions()
        resolved_type = self._resolve_type(source, artifact_type, filename)
        self._reject_legacy(source, resolved_type, filename)

        path, cleanup = self._as_path(source, filename)
        try:
            if not path.is_file():
                raise ArtifactNotFound(f"File not found: {path}")
            parser = parser_for(resolved_type)
            document = parser.parse(path, options)
            document.source = str(source) if not isinstance(source, bytes) else source_name(source, filename)
            from ._markdown_convertor import MarkdownConvertor

            document.markdown = MarkdownConvertor().convert(document).rstrip("\n")
            return document
        except (ArtifactNotFound, UnsupportedArtifact, EncryptedArtifact, CorruptArtifact, ArtifactParseError):
            raise
        except Exception as exc:
            raise ArtifactParseError(
                f"Unexpected parse failure for {source_name(source, filename)}: {exc}"
            ) from exc
        finally:
            if cleanup:
                path.unlink(missing_ok=True)

    def create(self, spec: ArtifactSpec | dict, *, dest: Path | None = None) -> ArtifactDocument:
        """Write a new artifact from ArtifactSpec (or JSON dict) and re-parse it."""
        resolved = coerce_spec(spec)
        dest_path = Path(dest) if dest is not None else self._temp_dest(resolved.filename, resolved.artifact_type)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        writer = writer_for(resolved.artifact_type)
        try:
            writer.write(resolved, dest_path)
        except ArtifactWriteError:
            raise
        except Exception as exc:
            raise ArtifactWriteError(f"Failed to create {dest_path.name}: {exc}") from exc
        if not dest_path.is_file():
            raise ArtifactWriteError(f"Writer did not produce a file: {dest_path}")
        document = self.parse(dest_path, resolved.artifact_type, filename=resolved.filename or dest_path.name)
        document.source = str(dest_path)
        return document

    def update(
        self,
        source: str | Path | bytes,
        ops: list[PatchOp | dict],
        *,
        dest: Path | None = None,
        filename: str | None = None,
    ) -> ArtifactDocument:
        """Apply ordered patch ops, write dest (default overwrite/temp), re-parse."""
        resolved_ops = coerce_ops(ops)
        resolved_type = self._resolve_type(source, None, filename)
        self._reject_legacy(source, resolved_type, filename)
        path, cleanup = self._as_path(source, filename)
        try:
            if not path.is_file():
                raise ArtifactNotFound(f"File not found: {path}")
            parsed = self.parse(path, resolved_type, filename=filename or path.name)
            dest_path = Path(dest) if dest is not None else (
                path if not cleanup else self._temp_dest(filename or path.name, resolved_type)
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if not resolved_ops:
                if dest_path.resolve() != path.resolve():
                    shutil.copy2(path, dest_path)
                parsed.source = str(dest_path)
                if dest_path.resolve() != path.resolve():
                    parsed = self.parse(dest_path, resolved_type, filename=dest_path.name)
                    parsed.source = str(dest_path)
                return parsed
            if resolved_type == ArtifactType.PDF:
                spec = document_to_spec(parsed)
                apply_ops_to_spec(spec, resolved_ops)
                spec.filename = dest_path.name
                return self.create(spec, dest=dest_path)
            writer = writer_for(resolved_type)
            try:
                writer.apply_ops(path, parsed, resolved_ops, dest_path)
            except ArtifactPatchError:
                raise
            except Exception as exc:
                raise ArtifactPatchError(f"Failed to apply patch ops to {path.name}: {exc}") from exc
            document = self.parse(dest_path, resolved_type, filename=dest_path.name)
            document.source = str(dest_path)
            return document
        except (ArtifactNotFound, UnsupportedArtifact, EncryptedArtifact, CorruptArtifact, ArtifactParseError, ArtifactPatchError, ArtifactWriteError):
            raise
        finally:
            if cleanup:
                path.unlink(missing_ok=True)

    def _temp_dest(self, filename: str | None, artifact_type: ArtifactType) -> Path:
        suffix = Path(filename).suffix.lower() if filename else ""
        if suffix not in PARSEABLE_EXTENSIONS[artifact_type]:
            suffix = WRITE_EXTENSIONS[artifact_type]
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="artifact-")
        handle.close()
        return Path(handle.name)

    def _resolve_type(
        self,
        source: str | Path | bytes,
        artifact_type: ArtifactType | str | None,
        filename: str | None,
    ) -> ArtifactType:
        if artifact_type is None:
            return self.classify(source, filename=filename)
        if isinstance(artifact_type, ArtifactType):
            return artifact_type
        try:
            return ArtifactType(str(artifact_type).strip().lower())
        except ValueError as exc:
            raise UnsupportedArtifact(
                f"Unknown artifact type '{artifact_type}'. "
                f"Expected one of: {', '.join(t.value for t in self.SUPPORTED_TYPES)}"
            ) from exc

    def _reject_legacy(
        self,
        source: str | Path | bytes,
        artifact_type: ArtifactType,
        filename: str | None,
    ) -> None:
        name = source_name(source, filename)
        ext = Path(name).suffix.lower()
        allowed = PARSEABLE_EXTENSIONS[artifact_type]
        if ext in LEGACY_EXTENSIONS or self._classifier.is_legacy(source, filename=filename):
            hint = LEGACY_OLE_HINT.get(artifact_type, "legacy Office binary")
            raise UnsupportedArtifact(
                f"{name} looks like {hint}. Convert to {sorted(allowed)} before parsing."
            )

    def _as_path(
        self,
        source: str | Path | bytes,
        filename: str | None,
    ) -> tuple[Path, bool]:
        if isinstance(source, bytes):
            suffix = Path(filename or "upload.bin").suffix or ".bin"
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            handle.write(source)
            handle.close()
            return Path(handle.name), True
        return Path(source), False
