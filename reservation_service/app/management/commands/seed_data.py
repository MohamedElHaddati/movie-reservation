from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.models import Movie, Seat, Showtime

TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/original"

GENRE_LABELS = {
    12: "Adventure",
    14: "Fantasy",
    16: "Animation",
    18: "Drama",
    27: "Horror",
    28: "Action",
    35: "Comedy",
    53: "Thriller",
    80: "Crime",
    878: "Sci-Fi",
    9648: "Mystery",
    10402: "Music",
    10749: "Romance",
    10751: "Family",
}

MOVIES_DATA = [
    {
        "id": 1439930,
        "title": "A Marvel Television Special Presentation - The Punisher: One Last Kill",
        "poster_path": "/gOggsBCSypNXq0yApYeXe7nnopT.jpg",
        "genre_ids": [28, 18, 80],
    },
    {
        "id": 687163,
        "title": "Project Hail Mary",
        "poster_path": "/yihdXomYb5kTeSivtFndMy5iDmf.jpg",
        "genre_ids": [878, 12],
    },
    {
        "id": 1339713,
        "title": "Obsession",
        "poster_path": "/40I66L7QKguTFDPvcLcdiTbAD7I.jpg",
        "genre_ids": [27],
    },
    {
        "id": 1582770,
        "title": "Dhurandhar: The Revenge",
        "poster_path": "/ov8vrRLZGoXHpYjSY9Vpv1tHJX7.jpg",
        "genre_ids": [28, 80, 53],
    },
    {
        "id": 931285,
        "title": "Mortal Kombat II",
        "poster_path": "/lIsMeDbwntNXSUVHmWMMRXEZOVc.jpg",
        "genre_ids": [28, 14, 12],
    },
    {
        "id": 936075,
        "title": "Michael",
        "poster_path": "/tMy2gc02azAGCskTzbfWPXZsK9w.jpg",
        "genre_ids": [10402, 18],
    },
    {
        "id": 1330021,
        "title": "Remarkably Bright Creatures",
        "poster_path": "/9HcEqn3D4J6b2Z0jK54id9nA0fr.jpg",
        "genre_ids": [18, 9648],
    },
    {
        "id": 1684226,
        "title": "Bride of the Year",
        "poster_path": "/2AiO7wnTrY5ktq0pLco3eS6g8NL.jpg",
        "genre_ids": [35, 10749],
    },
    {
        "id": 1140521,
        "title": "The Magic Faraway Tree",
        "poster_path": "/udXvLxC5gAqN8SinemyFBEcHpTf.jpg",
        "genre_ids": [10751, 14, 12],
    },
    {
        "id": 1007757,
        "title": "Swapped",
        "poster_path": "/tHhxWxge06goXU6ZQH1hj7vK8Hd.jpg",
        "genre_ids": [16, 10751, 12, 14],
    },
    {
        "id": 1314481,
        "title": "The Devil Wears Prada 2",
        "poster_path": "/xTI42pmsP5EDnvsNJPEDubwWBQO.jpg",
        "genre_ids": [35, 18],
    },
    {
        "id": 1226863,
        "title": "The Super Mario Galaxy Movie",
        "poster_path": "/eJGWx219ZcEMVQJhAgMiqo8tYY.jpg",
        "genre_ids": [10751, 35, 12, 14, 16],
    },
    {
        "id": 855435,
        "title": "Faces of Death",
        "poster_path": "/vPVY3S57lEooBLJCg6KGdMHkUxm.jpg",
        "genre_ids": [27],
    },
    {
        "id": 1455079,
        "title": "You, Me & Tuscany",
        "poster_path": "/mJS0IF7Af3WpPRhSTDT6rGpiLzw.jpg",
        "genre_ids": [10749, 35],
    },
    {
        "id": 1122573,
        "title": "In the Grey",
        "poster_path": "/83YeicHJqiyGGH1QRbeQdtqegvW.jpg",
        "genre_ids": [28, 53],
    },
    {
        "id": 1228710,
        "title": "Star Wars: The Mandalorian and Grogu",
        "poster_path": "/5Vi8dSauVwH1HOsiZceDMbRr1Ca.jpg",
        "genre_ids": [12, 878, 28],
    },
    {
        "id": 1301421,
        "title": "The Sheep Detectives",
        "poster_path": "/6QtL9rl3Zb4d8qW6EJ4qO5hSSfU.jpg",
        "genre_ids": [35, 10751, 9648],
    },
    {
        "id": 1327819,
        "title": "Hoppers",
        "poster_path": "/xjtWQ2CL1mpmMNwuU5HeS4Iuwuu.jpg",
        "genre_ids": [16, 12, 35, 10751, 878],
    },
    {
        "id": 1318447,
        "title": "Apex",
        "poster_path": "/eTp7gSPkSF3Aw79mNx1NkBP1PZT.jpg",
        "genre_ids": [28, 53],
    },
    {
        "id": 969681,
        "title": "Spider-Man: Brand New Day",
        "poster_path": "/yyB2VJEW3an2xCdcYCPQhn9QERR.jpg",
        "genre_ids": [878, 28, 12],
    },
]


def _movie_format(genre_ids):
    genre_set = set(genre_ids)
    if genre_set & {28, 12, 14, 878}:
        return Movie.Format.IMAX
    if genre_set & {16, 10751}:
        return Movie.Format.VF
    return Movie.Format.VO


def _movie_genre(genre_ids):
    labels = [GENRE_LABELS[genre_id] for genre_id in genre_ids if genre_id in GENRE_LABELS]
    if not labels:
        return "General"
    return ", ".join(labels[:2])


def _movie_duration(movie_id):
    return 95 + (movie_id % 70)


class Command(BaseCommand):
    help = "Seed movies, showtimes, seats, and default users."

    def handle(self, *args, **kwargs):
        base_date = timezone.localdate()
        created_showtimes = 0

        for movie_index, movie_data in enumerate(MOVIES_DATA):
            poster_path = movie_data.get("poster_path", "")
            poster_url = f"{TMDB_POSTER_BASE_URL}{poster_path}" if poster_path else ""

            movie, _ = Movie.objects.update_or_create(
                title=movie_data["title"],
                defaults={
                    "duration_min": _movie_duration(movie_data["id"]),
                    "genre": _movie_genre(movie_data["genre_ids"]),
                    "format": _movie_format(movie_data["genre_ids"]),
                    "poster_url": poster_url,
                },
            )

            for slot, hour in enumerate((18, 21)):
                showtime_dt = timezone.make_aware(
                    datetime.combine(base_date + timedelta(days=movie_index), time(hour=hour))
                )
                showtime, created = Showtime.objects.get_or_create(
                    movie=movie,
                    datetime=showtime_dt,
                    hall=f"HALL-{(movie_index % 6) + 1}",
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Movies seeded: {len(MOVIES_DATA)}. Showtimes created: {created_showtimes}"
            )
        )
