from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.services.certificate_generator import (
    CertificateData,
    CertificateGenerationError,
    CertificateGenerator,
)
from app.services.storage_service import LocalStorageService, StorageError


def _data(**overrides) -> CertificateData:
    base = CertificateData(
        recipient_name="Jane Doe",
        certificate_title="Certificate of Completion",
        course_name="Advanced Python Programming",
        issue_date=date(2026, 1, 15),
        certificate_number="CERT-2026-TESTID01",
    )
    return replace(base, **overrides)


def test_generate_creates_pdf_in_storage(tmp_path):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)

    key = generator.generate(_data())

    assert key == "CERT-2026-TESTID01.pdf"
    assert storage.exists(key) is True
    assert storage.get(key).startswith(b"%PDF")


def test_generated_pdf_contains_required_fields(tmp_path):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)
    data = _data()

    key = generator.generate(data)
    pdf_bytes = storage.get(key)

    text = PdfReader(BytesIO(pdf_bytes)).pages[0].extract_text()

    assert data.recipient_name in text
    assert data.course_name in text
    assert data.certificate_number in text
    assert data.issue_date.isoformat() in text


def test_render_is_pure_and_does_not_touch_storage(tmp_path):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)

    pdf_bytes = generator.render(_data())

    assert pdf_bytes.startswith(b"%PDF")
    assert list(Path(tmp_path).iterdir()) == []


def test_generate_rejects_blank_recipient_name(tmp_path):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)

    with pytest.raises(CertificateGenerationError):
        generator.generate(_data(recipient_name="   "))


def test_generate_wraps_render_failures(tmp_path, monkeypatch):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)

    def boom(*args, **kwargs):
        raise RuntimeError("reportlab exploded")

    monkeypatch.setattr("app.services.certificate_generator.draw_certificate", boom)

    with pytest.raises(CertificateGenerationError):
        generator.generate(_data())


def test_generate_wraps_storage_failures(tmp_path, monkeypatch):
    storage = LocalStorageService(str(tmp_path))
    generator = CertificateGenerator(storage)

    def boom(key, content):
        raise StorageError("disk full")

    monkeypatch.setattr(storage, "save", boom)

    with pytest.raises(CertificateGenerationError):
        generator.generate(_data())
