from django.contrib import admin
from reservation.models import Movie, Showtime, Seat, Reservation, Ticket, Payment

admin.site.register(Movie)
admin.site.register(Showtime)
admin.site.register(Seat)
admin.site.register(Reservation)
admin.site.register(Ticket)
admin.site.register(Payment)
