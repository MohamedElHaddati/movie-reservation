from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Movie, Reservation, Seat, Showtime


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


class ReservationSerializer(serializers.ModelSerializer):
    seats = serializers.PrimaryKeyRelatedField(many=True, queryset=Seat.objects.all())

    class Meta:
        model = Reservation
        fields = ["id", "user", "showtime", "seats", "created_at", "status"]
        read_only_fields = ["id", "user", "created_at", "status"]

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
