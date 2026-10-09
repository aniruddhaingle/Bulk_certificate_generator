from datetime import date
from typing import BinaryIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

PAGE_SIZE = landscape(A4)
ACCENT_COLOR = colors.HexColor("#1F3B57")


def draw_certificate(
    buffer: BinaryIO,
    *,
    recipient_name: str,
    certificate_title: str,
    course_name: str,
    issue_date: date,
    certificate_number: str,
) -> None:
    """Render a single-page certificate onto `buffer`. Pure drawing logic only —
    no filesystem, database, or queue knowledge."""
    width, height = PAGE_SIZE
    pdf = canvas.Canvas(buffer, pagesize=PAGE_SIZE)

    pdf.setStrokeColor(ACCENT_COLOR)
    pdf.setLineWidth(3)
    pdf.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)
    pdf.setLineWidth(0.75)
    pdf.rect(1.6 * cm, 1.6 * cm, width - 3.2 * cm, height - 3.2 * cm)

    pdf.setFont("Helvetica-Bold", 30)
    pdf.setFillColor(ACCENT_COLOR)
    pdf.drawCentredString(width / 2, height - 4.5 * cm, certificate_title.upper())

    pdf.setFont("Helvetica", 14)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(width / 2, height - 6.2 * cm, "This certificate is proudly presented to")

    pdf.setFont("Helvetica-Bold", 26)
    pdf.setFillColor(ACCENT_COLOR)
    pdf.drawCentredString(width / 2, height - 7.8 * cm, recipient_name)

    pdf.setFont("Helvetica", 14)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(width / 2, height - 9.2 * cm, "for successfully completing")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 10.4 * cm, course_name)

    pdf.setFont("Helvetica", 11)
    pdf.drawString(2.5 * cm, 2.5 * cm, f"Issue date: {issue_date.isoformat()}")
    pdf.drawRightString(width - 2.5 * cm, 2.5 * cm, f"Certificate ID: {certificate_number}")

    pdf.showPage()
    pdf.save()
