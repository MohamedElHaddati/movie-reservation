from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MovieViewSet, ReservationViewSet, SeatViewSet, ShowtimeViewSet

router = DefaultRouter()
router.register("movies", MovieViewSet, basename="movie")
router.register("showtimes", ShowtimeViewSet, basename="showtime")
router.register("seats", SeatViewSet, basename="seat")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [
    path("", include(router.urls)),
]
