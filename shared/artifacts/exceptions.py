from __future__ import annotations


class ArtifactError(Exception):
    """Base error for artifact handling."""


class ArtifactNotFound(ArtifactError, FileNotFoundError):
    """Source path does not exist."""


class UnsupportedArtifact(ArtifactError, ValueError):
    """Format cannot be classified or parsed."""


class EncryptedArtifact(ArtifactError, PermissionError):
    """File is encrypted and cannot be opened with the given credentials."""


class CorruptArtifact(ArtifactError):
    """File exists but is not a readable document of the claimed type."""


class ArtifactParseError(ArtifactError):
    """Parser failed while extracting content."""


class ArtifactWriteError(ArtifactError):
    """Writer failed while creating a file from an ArtifactSpec."""


class ArtifactPatchError(ArtifactError, ValueError):
    """Patch op is unknown, malformed, or does not match a block."""
