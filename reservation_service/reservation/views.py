from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from reservation.models import Movie, Showtime, Seat, Reservation, Payment
from reservation.publisher import publish_reservation_confirmed
from reservation.serializers import (
    MovieSerializer,
    SeatSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
)


class MovieListView(APIView):
    def get(self, request):
        movies = Movie.objects.all().order_by('title')
        return Response(MovieSerializer(movies, many=True).data)


class ShowtimeSeatsView(APIView):
    def get(self, request, showtime_id):
        showtime = get_object_or_404(Showtime, id=showtime_id)
        seats = showtime.seats.all().order_by('seat_number')
        return Response(SeatSerializer(seats, many=True).data)


class ReservationCreateView(APIView):
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            showtime = get_object_or_404(Showtime, id=data['showtime_id'])
            seats = list(Seat.objects.select_for_update().filter(showtime=showtime, id__in=data['seat_ids']))
            if len(seats) != len(data['seat_ids']):
                return Response({'detail': 'One or more seats are invalid.'}, status=status.HTTP_400_BAD_REQUEST)
            if any(seat.is_taken for seat in seats):
                return Response({'detail': 'One or more seats already taken.'}, status=status.HTTP_409_CONFLICT)

            reservation = Reservation.objects.create(
                user_id=data['user_id'],
                user_email=data['user_email'],
                showtime=showtime,
            )
            reservation.seats.set(seats)

            amount = Decimal('75.00') * Decimal(len(seats))
            Payment.objects.create(reservation=reservation, amount=amount, currency='MAD', status='pending')

        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class ReservationConfirmView(APIView):
    def post(self, request, reservation_id):
        with transaction.atomic():
            reservation = get_object_or_404(Reservation.objects.select_for_update(), id=reservation_id)
            if reservation.status != 'pending':
                return Response({'detail': 'Reservation is not pending.'}, status=status.HTTP_400_BAD_REQUEST)

            seats = list(reservation.seats.select_for_update())
            if any(seat.is_taken for seat in seats):
                return Response({'detail': 'One or more seats already taken.'}, status=status.HTTP_409_CONFLICT)

            for seat in seats:
                seat.is_taken = True
                seat.save(update_fields=['is_taken'])

            reservation.status = 'confirmed'
            reservation.save(update_fields=['status'])
            reservation.payment.status = 'paid'
            reservation.payment.save(update_fields=['status'])

        publish_reservation_confirmed({
            'reservation_id': reservation.id,
            'user_id': reservation.user_id,
            'user_email': reservation.user_email,
            'showtime_id': reservation.showtime_id,
            'seat_numbers': [seat.seat_number for seat in reservation.seats.all()],
            'amount': str(reservation.payment.amount),
            'currency': reservation.payment.currency,
        })

        return Response(ReservationSerializer(reservation).data)
