from django.urls import path
from webapp.views import movies_view, seats_view, checkout_view, confirmation_view

urlpatterns = [
    path('', movies_view, name='movies'),
    path('showtimes/<int:showtime_id>/seats/', seats_view, name='seats'),
    path('checkout/', checkout_view, name='checkout'),
    path('confirmation/<int:reservation_id>/', confirmation_view, name='confirmation'),
]
