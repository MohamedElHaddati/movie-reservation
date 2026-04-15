from django.urls import path
from reservation.views import MovieListView, ShowtimeSeatsView, ReservationCreateView, ReservationConfirmView

urlpatterns = [
    path('movies/', MovieListView.as_view(), name='movies'),
    path('showtimes/<int:showtime_id>/seats/', ShowtimeSeatsView.as_view(), name='showtime-seats'),
    path('reservations/', ReservationCreateView.as_view(), name='reservation-create'),
    path('reservations/<int:reservation_id>/confirm/', ReservationConfirmView.as_view(), name='reservation-confirm'),
]
