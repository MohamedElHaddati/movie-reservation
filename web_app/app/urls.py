from django.urls import path

from .views import (
    checkout_view,
    confirmation_view,
    login_view,
    logout_view,
    movies_view,
    register_view,
    reservation_detail_view,
    reservation_ticket_download_view,
    reservation_ticket_resend_view,
    reservation_ticket_view,
    reservations_view,
    seats_view,
)

urlpatterns = [
    path("", movies_view, name="movies"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("reservations/", reservations_view, name="reservations"),
    path("reservations/<int:reservation_id>/", reservation_detail_view, name="reservation_detail"),
    path("reservations/<int:reservation_id>/ticket/", reservation_ticket_view, name="reservation_ticket"),
    path(
        "reservations/<int:reservation_id>/ticket/download/",
        reservation_ticket_download_view,
        name="reservation_ticket_download",
    ),
    path(
        "reservations/<int:reservation_id>/ticket/resend/",
        reservation_ticket_resend_view,
        name="reservation_ticket_resend",
    ),
    path("showtimes/<int:showtime_id>/seats/", seats_view, name="seats"),
    path("showtimes/<int:showtime_id>/checkout/", checkout_view, name="checkout"),
    path("showtimes/<int:showtime_id>/confirmation/", confirmation_view, name="confirmation"),
]
