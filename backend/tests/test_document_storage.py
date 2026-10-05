from pathlib import Path

import pytest

from app.integrations.storage.local import (
    InvalidDocument,
    LocalSourceStorage,
    fingerprint,
    safe_filename,
    validate_upload,
)


def test_safe_paths_and_immutable_original(tmp_path):
    storage = LocalSourceStorage(tmp_path)
    for key in ("../escape.pdf", "/tmp/escape.pdf", "a/../../escape.pdf", "."):
        with pytest.raises(InvalidDocument):
            storage.path(key)
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(InvalidDocument):
        storage.path("linked/escape.pdf")
    content = b"%PDF-1.7\noriginal"
    key = storage.save(content, 1, 2, 1)
    assert storage.read(key) == content
    assert storage.path(key).stat().st_mode & 0o222 == 0
    assert Path(key).name == "source.pdf"
    assert len(fingerprint(content)) == 64
    assert fingerprint(content) != fingerprint(content + b"x")
    assert safe_filename("../../unsafe/name.pdf") == "name.pdf"


def test_upload_validation():
    validate_upload(b"%PDF-1.7", "test.pdf", "application/pdf", 1024)
    for data, name, mime in (
        (b"", "x.pdf", "application/pdf"),
        (b"%PDF-" * 300, "x.pdf", "application/pdf"),
        (b"hello", "x.pdf", "application/pdf"),
        (b"%PDF-1.7", "x.exe", "application/pdf"),
        (b"%PDF-1.7", "x.pdf", "text/html"),
    ):
        with pytest.raises(InvalidDocument):
            validate_upload(data, name, mime, 1024)
