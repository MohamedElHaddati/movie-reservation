import os
from decimal import Decimal
from pathlib import Path

from django.http import FileResponse
from django.db import transaction
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from . import publisher
from .models import Movie, Payment, Reservation, Seat, Showtime, Ticket
from .serializers import (
    MovieSerializer,
    ReservationSerializer,
    SeatSerializer,
    ShowtimeSerializer,
    UserRegistrationSerializer,
)

class AdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class ReservationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        if view.action in ["list", "retrieve", "create", "confirm", "ticket", "ticket_download", "ticket_resend"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user_id == request.user.id


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().order_by("id")
    serializer_class = MovieSerializer
    permission_classes = [AdminOrReadOnly]


class ShowtimeViewSet(viewsets.ModelViewSet):
    queryset = Showtime.objects.select_related("movie").all().order_by("datetime")
    serializer_class = ShowtimeSerializer
    permission_classes = [AdminOrReadOnly]


class SeatViewSet(viewsets.ModelViewSet):
    serializer_class = SeatSerializer
    permission_classes = [AdminOrReadOnly]

    def get_queryset(self):
        queryset = Seat.objects.select_related("showtime", "showtime__movie").all().order_by("seat_number")
        showtime_id = self.request.query_params.get("showtime")
        if showtime_id:
            queryset = queryset.filter(showtime_id=showtime_id)
        return queryset


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [ReservationPermission]

    def get_queryset(self):
        queryset = Reservation.objects.select_related(
            "user",
            "showtime",
            "showtime__movie",
            "payment",
            "ticket",
        ).prefetch_related("seats")
        if self.request.user.is_staff:
            return queryset.order_by("-created_at")
        return queryset.filter(user=self.request.user).order_by("-created_at")

    def _ticket_path(self, reservation):
        try:
            return Path(reservation.ticket.pdf_path)
        except Ticket.DoesNotExist:
            tickets_dir = Path(os.environ.get("TICKETS_DIR", "/tickets"))
            return tickets_dir / f"{reservation.id}.pdf"

    @action(detail=True, methods=["patch"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        reservation = self.get_object()

        if reservation.status != Reservation.Status.CONFIRMED:
            reservation.status = Reservation.Status.CONFIRMED
            reservation.save(update_fields=["status"])

            seat_count = reservation.seats.count()
            Payment.objects.update_or_create(
                reservation=reservation,
                defaults={
                    "amount": Decimal("50.00") * seat_count,
                    "currency": "MAD",
                    "status": Payment.Status.PAID,
                },
            )
            reservation.seats.update(is_taken=True)
            transaction.on_commit(lambda reservation_id=reservation.id: publisher.publish_reservation_confirmed(reservation_id))

        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="ticket")
    def ticket(self, request, pk=None):
        reservation = self.get_object()
        ticket_path = self._ticket_path(reservation)

        generated_at = None
        try:
            generated_at = reservation.ticket.generated_at
        except Ticket.DoesNotExist:
            pass

        serializer = self.get_serializer(reservation)
        return Response(
            {
                "reservation": serializer.data,
                "ticket": {
                    "available": ticket_path.exists(),
                    "generated_at": generated_at,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="ticket/download")
    def ticket_download(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != Reservation.Status.CONFIRMED:
            return Response(
                {"detail": "Ticket is available only for confirmed reservations."},
                status=status.HTTP_409_CONFLICT,
            )

        ticket_path = self._ticket_path(reservation)
        if not ticket_path.exists():
            return Response(
                {"detail": "Ticket is not generated yet. Please try again shortly."},
                status=status.HTTP_404_NOT_FOUND,
            )

        download = request.query_params.get("download", "0") == "1"
        return FileResponse(
            ticket_path.open("rb"),
            content_type="application/pdf",
            as_attachment=download,
            filename=f"cinebook-ticket-{reservation.id}.pdf",
        )

    @action(detail=True, methods=["post"], url_path="ticket/resend")
    def ticket_resend(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status != Reservation.Status.CONFIRMED:
            return Response(
                {"detail": "Only confirmed reservations can resend tickets."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        publisher.publish_reservation_confirmed(reservation.id)
        return Response({"detail": "Ticket resend requested."}, status=status.HTTP_202_ACCEPTED)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
