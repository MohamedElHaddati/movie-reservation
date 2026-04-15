from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservation.models import Movie, Showtime, Seat


class Command(BaseCommand):
    help = 'Seed 3 movies with 2 showtimes each and 40 seats per showtime.'

    def handle(self, *args, **options):
        movies_data = [
            {'title': 'Interstellar', 'duration': 169, 'genre': 'Sci-Fi', 'format': 'IMAX'},
            {'title': 'Inception', 'duration': 148, 'genre': 'Sci-Fi', 'format': 'VO'},
            {'title': 'Dune: Part Two', 'duration': 166, 'genre': 'Sci-Fi', 'format': 'VF'},
        ]

        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        created_showtimes = 0

        for idx, movie_data in enumerate(movies_data):
            movie, _ = Movie.objects.get_or_create(title=movie_data['title'], defaults=movie_data)

            for slot in range(2):
                show_dt = base_time + timedelta(days=idx, hours=slot * 3)
                showtime, _ = Showtime.objects.get_or_create(
                    movie=movie,
                    datetime=show_dt,
                    hall=f'H{idx + 1}',
                )
                created_showtimes += 1

                for seat_no in range(1, 41):
                    Seat.objects.get_or_create(
                        showtime=showtime,
                        seat_number=f'S{seat_no:02d}',
                        defaults={'is_taken': False},
                    )

        self.stdout.write(self.style.SUCCESS(f'Seed complete: 3 movies, {created_showtimes} showtimes, 40 seats/showtime.'))
