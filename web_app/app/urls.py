from django.urls import path

from .views import checkout_view, confirmation_view, login_view, logout_view, movies_view, register_view, seats_view

urlpatterns = [
    path("", movies_view, name="movies"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("showtimes/<int:showtime_id>/seats/", seats_view, name="seats"),
    path("showtimes/<int:showtime_id>/checkout/", checkout_view, name="checkout"),
    path("showtimes/<int:showtime_id>/confirmation/", confirmation_view, name="confirmation"),
]
