import os
from pathlib import Path

from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_ticket_pdf(reservation_id, payload):
    tickets_dir = Path(os.environ.get('TICKETS_DIR', settings.TICKETS_DIR))
    tickets_dir.mkdir(parents=True, exist_ok=True)
    file_path = tickets_dir / f'ticket_{reservation_id}.pdf'

    c = canvas.Canvas(str(file_path), pagesize=A4)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(72, 800, 'Cinebook Ticket Confirmation')

    c.setFont('Helvetica', 12)
    c.drawString(72, 760, f"Reservation ID: {reservation_id}")
    c.drawString(72, 740, f"User: {payload.get('user_id')}")
    c.drawString(72, 720, f"Showtime ID: {payload.get('showtime_id')}")
    c.drawString(72, 700, f"Seats: {', '.join(payload.get('seat_numbers', []))}")
    c.drawString(72, 680, f"Amount: {payload.get('amount')} {payload.get('currency', 'MAD')}")

    c.showPage()
    c.save()
    return str(file_path)
