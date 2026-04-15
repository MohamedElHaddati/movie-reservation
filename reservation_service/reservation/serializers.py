from rest_framework import serializers
from reservation.models import Movie, Showtime, Seat, Reservation


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['id', 'title', 'duration', 'genre', 'format']


class ShowtimeSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)

    class Meta:
        model = Showtime
        fields = ['id', 'movie', 'datetime', 'hall']


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'is_taken']


class ReservationCreateSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=100)
    user_email = serializers.EmailField()
    showtime_id = serializers.IntegerField()
    seat_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class ReservationSerializer(serializers.ModelSerializer):
    seats = SeatSerializer(many=True, read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'user_id', 'user_email', 'showtime', 'created_at', 'status', 'seats']
