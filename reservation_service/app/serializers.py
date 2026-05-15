from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Movie, Payment, Reservation, Seat, Showtime, Ticket


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = "__all__"


class ShowtimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Showtime
        fields = "__all__"


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = "__all__"


class ReservationMovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "title", "genre", "format", "duration_min", "poster_url"]


class ReservationShowtimeSerializer(serializers.ModelSerializer):
    movie = ReservationMovieSerializer(read_only=True)

    class Meta:
        model = Showtime
        fields = ["id", "datetime", "hall", "movie"]


class ReservationSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["id", "seat_number", "is_taken"]


class ReservationPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["amount", "currency", "status"]


class ReservationTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["pdf_path", "generated_at"]


class ReservationSerializer(serializers.ModelSerializer):
    seats = serializers.PrimaryKeyRelatedField(many=True, queryset=Seat.objects.all(), write_only=True)
    seat_details = ReservationSeatSerializer(source="seats", many=True, read_only=True)
    showtime_details = ReservationShowtimeSerializer(source="showtime", read_only=True)
    payment = ReservationPaymentSerializer(read_only=True)
    ticket = ReservationTicketSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "user",
            "showtime",
            "showtime_details",
            "seats",
            "seat_details",
            "created_at",
            "status",
            "payment",
            "ticket",
        ]
        read_only_fields = [
            "id",
            "user",
            "showtime_details",
            "seat_details",
            "created_at",
            "status",
            "payment",
            "ticket",
        ]

    def validate(self, attrs):
        showtime = attrs.get("showtime")
        seats = attrs.get("seats", [])

        if not seats:
            raise serializers.ValidationError("At least one seat must be selected.")

        for seat in seats:
            if seat.showtime_id != showtime.id:
                raise serializers.ValidationError("All seats must belong to the selected showtime.")
            if seat.is_taken:
                raise serializers.ValidationError(f"Seat {seat.seat_number} is already taken.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        seats = validated_data.pop("seats")
        request = self.context["request"]
        reservation = Reservation.objects.create(user=request.user, **validated_data)
        reservation.seats.set(seats)
        return reservation


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    class Meta:
        model = get_user_model()
        fields = ["username", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)
