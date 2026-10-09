"""Proves duplicate task delivery is a genuine no-op end-to-end — calling the
actual task functions a second time, not just asserting on the repository's
claim-guard in isolation (test_job_repository.py already covers that)."""

from app.workers.tasks import generate_certificate, process_certificate_job


def _payload(n: int) -> dict:
    return {
        "certificate_title": "Certificate of Completion",
        "course_name": "Advanced Python Programming",
        "issue_date": "2026-01-15",
        "recipients": [{"name": f"Recipient {i}", "email": f"r{i}@example.com"} for i in range(n)],
    }


def test_generate_certificate_redelivery_does_not_double_count(client, eager_worker):
    created = client.post("/api/v1/certificate-jobs", json=_payload(1))
    job_id = created.json()["job_id"]
    certificate_id = client.get(f"/api/v1/certificate-jobs/{job_id}/certificates").json()["items"][0][
        "certificate_id"
    ]

    first_run_status = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert first_run_status["successful_count"] == 1
    assert first_run_status["status"] == "COMPLETED"

    # Simulate the broker redelivering the same task (e.g. after acks_late + a
    # worker crash that happened right after the ack but before termination).
    generate_certificate(certificate_id)

    second_run_status = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert second_run_status["successful_count"] == 1  # unchanged, not double-counted
    assert second_run_status["status"] == "COMPLETED"


def test_process_certificate_job_redelivery_does_not_redispatch(client, eager_worker):
    created = client.post("/api/v1/certificate-jobs", json=_payload(3))
    job_id = created.json()["job_id"]

    before = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert before["status"] == "COMPLETED"

    # Simulate the orchestrator task itself being redelivered.
    process_certificate_job(job_id)

    after = client.get(f"/api/v1/certificate-jobs/{job_id}").json()
    assert after == before
