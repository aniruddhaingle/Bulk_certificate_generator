from datetime import date

from app.utils.ids import generate_certificate_number


def test_certificate_number_format():
    number = generate_certificate_number(date(2026, 5, 1))

    assert number.startswith("CERT-2026-")
    assert len(number) == len("CERT-2026-") + 8


def test_certificate_number_defaults_to_current_year_when_no_date_given():
    number = generate_certificate_number()

    assert number.startswith(f"CERT-{date.today().year}-")


def test_certificate_number_is_unique_across_many_calls():
    numbers = {generate_certificate_number() for _ in range(1000)}

    assert len(numbers) == 1000
