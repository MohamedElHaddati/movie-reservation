from django.conf import settings
from django.db import models


class Movie(models.Model):
    class Format(models.TextChoices):
        IMAX = "IMAX", "IMAX"
        VF = "VF", "VF"
        VO = "VO", "VO"

    title = models.CharField(max_length=255)
    duration_min = models.PositiveIntegerField()
    genre = models.CharField(max_length=100)
    format = models.CharField(max_length=10, choices=Format.choices)

    def __str__(self):
        return self.title


class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="showtimes")
    datetime = models.DateTimeField()
    hall = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.movie.title} @ {self.datetime.isoformat()}"


class Seat(models.Model):
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    is_taken = models.BooleanField(default=False)

    class Meta:
        unique_together = ("showtime", "seat_number")

    def __str__(self):
        return f"{self.showtime_id}-{self.seat_number}"


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name="reservations")
    seats = models.ManyToManyField(Seat, related_name="reservations")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"Reservation {self.id} ({self.status})"


class Ticket(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="ticket")
    pdf_path = models.CharField(max_length=500)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.id} for reservation {self.reservation_id}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="MAD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"Payment {self.id} ({self.status})"
