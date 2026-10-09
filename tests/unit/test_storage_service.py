import pytest

from app.services.storage_service import LocalStorageService, StorageError


def test_save_and_get_roundtrip(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    key = storage.save("sub/dir/file.pdf", b"hello world")

    assert key == "sub/dir/file.pdf"
    assert storage.exists("sub/dir/file.pdf") is True
    assert storage.get("sub/dir/file.pdf") == b"hello world"


def test_exists_false_for_missing_key(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    assert storage.exists("nope.pdf") is False


def test_get_missing_key_raises_storage_error(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    with pytest.raises(StorageError):
        storage.get("missing.pdf")


def test_save_creates_root_directory_if_missing(tmp_path):
    root = tmp_path / "does" / "not" / "exist"
    storage = LocalStorageService(str(root))

    storage.save("a.pdf", b"data")

    assert (root / "a.pdf").is_file()


def test_save_rejects_path_traversal(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    with pytest.raises(StorageError):
        storage.save("../escape.pdf", b"data")


def test_get_rejects_path_traversal(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    with pytest.raises(StorageError):
        storage.get("../../etc/passwd")


def test_exists_returns_false_rather_than_raising_for_traversal_key(tmp_path):
    storage = LocalStorageService(str(tmp_path))

    assert storage.exists("../escape.pdf") is False
