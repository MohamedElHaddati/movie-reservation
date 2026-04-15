from django.db import models


class Movie(models.Model):
    FORMAT_CHOICES = [('IMAX', 'IMAX'), ('VF', 'VF'), ('VO', 'VO')]

    title = models.CharField(max_length=255)
    duration = models.PositiveIntegerField()
    genre = models.CharField(max_length=100)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    def __str__(self):
        return self.title


class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes')
    datetime = models.DateTimeField()
    hall = models.CharField(max_length=50)


class Seat(models.Model):
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_taken = models.BooleanField(default=False)

    class Meta:
        unique_together = ('showtime', 'seat_number')


class Reservation(models.Model):
    STATUS_CHOICES = [('pending', 'pending'), ('confirmed', 'confirmed'), ('cancelled', 'cancelled')]

    user_id = models.CharField(max_length=100)
    user_email = models.EmailField(default='client@cinebook.local')
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='reservations')
    seats = models.ManyToManyField(Seat, related_name='reservations')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


class Ticket(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='ticket')
    pdf_path = models.CharField(max_length=500)
    generated_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    STATUS_CHOICES = [('pending', 'pending'), ('paid', 'paid'), ('failed', 'failed')]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='MAD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
