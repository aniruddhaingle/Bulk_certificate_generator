import uuid
from datetime import date


def generate_certificate_number(issue_date: date | None = None) -> str:
    """Server-generated, human-readable certificate ID. Never derived from client input."""
    year = (issue_date or date.today()).year
    suffix = uuid.uuid4().hex[:8].upper()
    return f"CERT-{year}-{suffix}"
