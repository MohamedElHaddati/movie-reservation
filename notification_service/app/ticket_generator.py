import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate(reservation, seats):
    tickets_dir = Path(os.environ.get("TICKETS_DIR", "/tickets"))
    tickets_dir.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_dir / f"{reservation.id}.pdf"

    c = canvas.Canvas(str(ticket_path), pagesize=A4)
    width, height = A4

    movie_title = reservation.showtime.movie.title
    showtime_text = reservation.showtime.datetime.strftime("%Y-%m-%d %H:%M")
    seats_text = ", ".join(sorted(seat.seat_number for seat in seats))
    booking_ref = f"CB-{reservation.id:06d}"

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 80, "CineBook Ticket")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 130, f"Booking reference: {booking_ref}")
    c.drawString(50, height - 155, f"Movie: {movie_title}")
    c.drawString(50, height - 180, f"Showtime: {showtime_text}")
    c.drawString(50, height - 205, f"Hall: {reservation.showtime.hall}")
    c.drawString(50, height - 230, f"Seats: {seats_text}")
    c.drawString(50, height - 270, "Please arrive 20 minutes before showtime.")
    c.showPage()
    c.save()

    return str(ticket_path)
