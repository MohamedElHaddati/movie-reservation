from django.conf import settings
from django.core.mail import EmailMessage


def send(reservation, ticket_path):
    movie_title = reservation.showtime.movie.title
    showtime_text = reservation.showtime.datetime.strftime("%Y-%m-%d %H:%M")
    seats = ", ".join(sorted(seat.seat_number for seat in reservation.seats.all()))
    booking_ref = f"CB-{reservation.id:06d}"

    subject = f"Your CineBook ticket — {movie_title}"
    body = (
        f"Hello {reservation.user.username},\n\n"
        f"Your reservation is confirmed.\n"
        f"Booking reference: {booking_ref}\n"
        f"Movie: {movie_title}\n"
        f"Showtime: {showtime_text}\n"
        f"Hall: {reservation.showtime.hall}\n"
        f"Seats: {seats}\n\n"
        "Enjoy your movie!"
    )

    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reservation.user.email],
    )
    message.attach_file(ticket_path)
    message.send(fail_silently=False)
