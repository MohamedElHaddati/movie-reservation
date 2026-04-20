from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import Movie, Seat, Showtime


class Command(BaseCommand):
    help = "Seed movies, showtimes, seats, and default users."

    def handle(self, *args, **kwargs):
        movies_data = [
            {"title": "Dune: Part Two", "duration_min": 166, "genre": "Sci-Fi", "format": "IMAX"},
            {"title": "The Batman", "duration_min": 176, "genre": "Action", "format": "VO"},
            {"title": "Inside Out 2", "duration_min": 96, "genre": "Animation", "format": "VF"},
        ]

        now = timezone.now()
        created_showtimes = 0

        for movie_index, movie_data in enumerate(movies_data):
            movie, _ = Movie.objects.get_or_create(
                title=movie_data["title"],
                defaults={
                    "duration_min": movie_data["duration_min"],
                    "genre": movie_data["genre"],
                    "format": movie_data["format"],
                },
            )
            for slot in range(2):
                showtime_dt = now + timedelta(days=movie_index, hours=slot * 3)
                showtime, created = Showtime.objects.get_or_create(
                    movie=movie,
                    datetime=showtime_dt,
                    hall=f"HALL-{movie_index + 1}",
                )
                if created:
                    created_showtimes += 1
                for row in ["A", "B", "C", "D", "E"]:
                    for seat_num in range(1, 9):
                        Seat.objects.get_or_create(
                            showtime=showtime,
                            seat_number=f"{row}{seat_num}",
                            defaults={"is_taken": False},
                        )

        user_model = get_user_model()
        if not user_model.objects.filter(username="admin").exists():
            user_model.objects.create_superuser(
                username="admin",
                email="admin@cinebook.local",
                password="admin12345",
            )
        if not user_model.objects.filter(username="client").exists():
            user_model.objects.create_user(
                username="client",
                email="client@cinebook.local",
                password="client12345",
            )

        self.stdout.write(self.style.SUCCESS(f"Seed complete. Showtimes created: {created_showtimes}"))
