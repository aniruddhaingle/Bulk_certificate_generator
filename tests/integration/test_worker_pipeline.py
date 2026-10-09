from app.services.certificate_generator import CertificateGenerationError, CertificateGenerator


def _payload(names: list[str]) -> dict:
    return {
        "certificate_title": "Certificate of Completion",
        "course_name": "Advanced Python Programming",
        "issue_date": "2026-01-15",
        "recipients": [
            {"name": name, "email": f"{name.split()[0].lower()}@example.com"} for name in names
        ],
    }


def test_partial_failure_marks_job_completed_with_errors(client, eager_worker, monkeypatch):
    original_generate = CertificateGenerator.generate

    def flaky_generate(self, data):
        if data.recipient_name == "Unlucky Recipient":
            raise CertificateGenerationError("simulated failure for testing")
        return original_generate(self, data)

    monkeypatch.setattr(CertificateGenerator, "generate", flaky_generate)

    names = ["Alice One", "Bob Two", "Unlucky Recipient", "Carol Three", "Dave Four"]
    created = client.post("/api/v1/certificate-jobs", json=_payload(names))
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    status = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert status["status"] == "COMPLETED_WITH_ERRORS"
    assert status["total_count"] == 5
    assert status["successful_count"] == 4
    assert status["failed_count"] == 1
    assert status["pending_count"] == 0
    assert status["started_at"] is not None
    assert status["completed_at"] is not None

    certs = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates?page_size=10").json()["items"]
    assert len(certs) == 5
    # every certificate reached a terminal state - processing never stopped partway through
    assert {c["status"] for c in certs} <= {"COMPLETED", "FAILED"}

    failed = [c for c in certs if c["status"] == "FAILED"]
    succeeded = [c for c in certs if c["status"] == "COMPLETED"]
    assert len(failed) == 1
    assert len(succeeded) == 4
    assert failed[0]["recipient_name"] == "Unlucky Recipient"
    assert failed[0]["error_message"] is not None
    assert "simulated failure" in failed[0]["error_message"]

    # successful certificates remain available for download
    for cert in succeeded:
        download = client.get(cert["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/pdf"
        assert download.content.startswith(b"%PDF")

    # the failed certificate is correctly reported as not downloadable
    failed_download = client.get(failed[0]["download_url"])
    assert failed_download.status_code == 409
    assert "simulated failure" in failed_download.json()["error"]["context"]["error_message"]


def test_all_success_marks_job_completed(client, eager_worker):
    created = client.post("/api/v1/certificate-jobs", json=_payload(["Alice", "Bob", "Carol"]))
    job_id = created.json()["job_id"]

    status = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert status["status"] == "COMPLETED"
    assert status["successful_count"] == 3
    assert status["failed_count"] == 0
    assert status["pending_count"] == 0


def test_all_failure_marks_job_failed(client, eager_worker, monkeypatch):
    def always_fail(self, data):
        raise CertificateGenerationError("simulated total failure")

    monkeypatch.setattr(CertificateGenerator, "generate", always_fail)

    created = client.post("/api/v1/certificate-jobs", json=_payload(["Alice", "Bob"]))
    job_id = created.json()["job_id"]

    status = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert status["status"] == "FAILED"
    assert status["successful_count"] == 0
    assert status["failed_count"] == 2
