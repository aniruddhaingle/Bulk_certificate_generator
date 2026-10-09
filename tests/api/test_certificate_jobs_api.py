import uuid


def _payload(n: int = 2) -> dict:
    return {
        "certificate_title": "Certificate of Completion",
        "course_name": "Advanced Python Programming",
        "issue_date": "2026-01-15",
        "recipients": [{"name": f"Recipient {i}", "email": f"r{i}@example.com"} for i in range(n)],
    }


def test_create_job_success(client):
    response = client.post("/api/v1/certificate-jobs", json=_payload(3))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["total_count"] == 3
    assert body["successful_count"] == 0
    assert body["failed_count"] == 0
    assert "job_id" in body


def test_create_job_schedules_background_processing(client, mock_celery_dispatch):
    """A job isn't just a DB row — creating it must actually schedule the
    worker to process it. Proven by asserting the dispatch call itself,
    with the task mocked so this test covers only the API+DB boundary."""
    response = client.post("/api/v1/certificate-jobs", json=_payload(2))
    job_id = response.json()["job_id"]

    mock_celery_dispatch.delay.assert_called_once_with(job_id)


def test_create_job_marks_failed_when_dispatch_raises(client, mock_celery_dispatch):
    """If the broker is unreachable right after the job is committed, the job
    can't just vanish into a 500 — it already exists. It should come back as
    FAILED with a reason, which is exactly what job-level FAILED means."""
    mock_celery_dispatch.delay.side_effect = RuntimeError("redis unreachable")

    response = client.post("/api/v1/certificate-jobs", json=_payload(2))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "FAILED"

    status = client.get(f"/api/v1/certificate-jobs/{body['job_id']}").json()
    assert status["status"] == "FAILED"
    assert "redis unreachable" in status["error_summary"]


def test_create_job_persists_certificate_records(client):
    created = client.post("/api/v1/certificate-jobs", json=_payload(2))
    job_id = created.json()["job_id"]

    listed = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates")

    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 2
    assert {item["status"] for item in items} == {"PENDING"}
    assert len({item["certificate_number"] for item in items}) == 2  # unique per recipient


def test_get_job_status_success(client):
    created = client.post("/api/v1/certificate-jobs", json=_payload(2))
    job_id = created.json()["job_id"]

    response = client.get(f"/api/v1/certificate-jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["pending_count"] == 2
    assert body["successful_count"] == 0
    assert body["failed_count"] == 0
    assert body["status"] == "PENDING"
    assert body["started_at"] is None
    assert body["completed_at"] is None


def test_get_job_status_not_found(client):
    response = client.get(f"/api/v1/certificate-jobs/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_list_certificates_job_not_found(client):
    response = client.get(f"/api/v1/certificate-jobs/{uuid.uuid4()}/certificates")

    assert response.status_code == 404


def test_list_certificates_pagination(client):
    created = client.post("/api/v1/certificate-jobs", json=_payload(5))
    job_id = created.json()["job_id"]

    page1 = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates?page=1&page_size=2")
    page3 = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates?page=3&page_size=2")

    assert page1.json()["total"] == 5
    assert len(page1.json()["items"]) == 2
    assert len(page3.json()["items"]) == 1


def test_list_certificates_filter_by_status(client):
    created = client.post("/api/v1/certificate-jobs", json=_payload(2))
    job_id = created.json()["job_id"]

    failed_filter = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates?status=FAILED")
    pending_filter = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates?status=PENDING")

    assert failed_filter.json()["items"] == []
    assert len(pending_filter.json()["items"]) == 2
