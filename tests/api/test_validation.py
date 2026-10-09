"""Input-validation tests for POST /api/v1/certificate-jobs, isolated from
the happy-path/status tests so every rejection rule has one obvious home."""


def _payload(n: int = 2) -> dict:
    return {
        "certificate_title": "Certificate of Completion",
        "course_name": "Advanced Python Programming",
        "issue_date": "2026-01-15",
        "recipients": [{"name": f"Recipient {i}", "email": f"r{i}@example.com"} for i in range(n)],
    }


def test_empty_recipients_rejected(client):
    payload = _payload(0)
    payload["recipients"] = []

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any("recipients" in detail["field"] for detail in body["error"]["details"])


def test_invalid_email_rejected(client):
    payload = _payload(1)
    payload["recipients"][0]["email"] = "not-an-email"

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_blank_recipient_name_rejected(client):
    payload = _payload(1)
    payload["recipients"][0]["name"] = "   "

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_missing_required_top_level_field_rejected(client):
    payload = _payload(1)
    del payload["course_name"]

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_missing_recipient_name_rejected(client):
    payload = _payload(1)
    del payload["recipients"][0]["name"]

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_invalid_issue_date_rejected(client):
    payload = _payload(1)
    payload["issue_date"] = "not-a-date"

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_duplicate_recipients_in_same_request_rejected(client):
    payload = _payload(1)
    payload["recipients"].append(dict(payload["recipients"][0]))

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 422


def test_same_name_different_email_is_not_treated_as_duplicate(client):
    """Duplicate detection is keyed on (name, email) together — two
    different people can share a name."""
    payload = _payload(1)
    payload["recipients"].append({"name": payload["recipients"][0]["name"], "email": "someone-else@example.com"})

    response = client.post("/api/v1/certificate-jobs", json=payload)

    assert response.status_code == 202


def test_oversized_bulk_request_rejected(client, monkeypatch):
    from app.schemas import certificate_job as module

    monkeypatch.setattr(module.settings, "max_bulk_size", 3)
    response = client.post("/api/v1/certificate-jobs", json=_payload(4))

    assert response.status_code == 422


def test_request_exactly_at_bulk_limit_is_accepted(client, monkeypatch):
    from app.schemas import certificate_job as module

    monkeypatch.setattr(module.settings, "max_bulk_size", 3)
    response = client.post("/api/v1/certificate-jobs", json=_payload(3))

    assert response.status_code == 202


def test_malformed_job_id_in_path_rejected(client):
    response = client.get("/api/v1/certificate-jobs/not-a-valid-uuid")

    assert response.status_code == 422


def test_malformed_certificate_id_in_path_rejected(client):
    response = client.get("/api/v1/certificates/not-a-valid-uuid/download")

    assert response.status_code == 422
