"""Local immutable source storage. A malware scanner can precede save() later."""

import hashlib
import re
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class InvalidDocument(ValueError):
    pass


class SourceStorage(Protocol):
    def save(self, content: bytes, case_pk: int, document_pk: int, version: int) -> str: ...
    def read(self, key: str) -> bytes: ...
    def remove(self, key: str) -> None: ...


def safe_filename(name: str) -> str:
    leaf = (name or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    leaf = re.sub(r"[^a-zA-Z0-9 ._()-]", "_", leaf).strip(" .")
    return (leaf[:240] or "document") + ("" if leaf.lower().endswith(".pdf") else ".pdf")


def fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_upload(content: bytes, filename: str, mime_type: str | None, max_bytes: int):
    if not content or len(content) > max_bytes:
        raise InvalidDocument("PDF is empty or exceeds the upload limit")
    if not filename.lower().endswith(".pdf") or mime_type not in {
        "application/pdf",
        "application/octet-stream",
        None,
    }:
        raise InvalidDocument("Only PDF documents are supported")
    if not content.startswith(b"%PDF-"):
        raise InvalidDocument("File content is not a PDF")


class LocalSourceStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        candidate = Path(key)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise InvalidDocument("Invalid storage key")
        resolved = (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root) or resolved == self.root:
            raise InvalidDocument("Invalid storage key")
        return resolved

    def save(self, content: bytes, case_pk: int, document_pk: int, version: int) -> str:
        if min(case_pk, document_pk, version) < 1:
            raise InvalidDocument("Invalid internal storage identifier")
        key = f"cases/{case_pk}/documents/{document_pk}/versions/{version}/{uuid4().hex}/source.pdf"
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Recheck after creating directories; never follow an escaped symlink.
        path = self.path(key)
        with path.open("xb") as output:
            output.write(content)
        path.chmod(0o440)
        return key

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def remove(self, key: str) -> None:
        """Rollback cleanup only; there is no public document deletion operation."""
        self.path(key).unlink(missing_ok=True)
