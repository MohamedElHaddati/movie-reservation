Project: Movie ticket reservation system — microservices architecture, fully self-hosted on a single VPS using Docker Compose.
Stack: Python/Django, Django REST Framework, PostgreSQL, RabbitMQ, Mailhog (local email testing), Docker + Docker Compose. No AWS, no external cloud services.
Generate the complete project scaffold with the following structure:
cinebook/
├── gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── gateway/
│       ├── settings.py
│       ├── urls.py              # proxies routes to services
│       └── middleware.py        # JWT auth validation
├── reservation_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── reservation/
│       ├── settings.py
│       ├── urls.py
│       ├── models.py            # Movie, Showtime, Seat, Reservation, Ticket, Payment
│       ├── serializers.py
│       ├── views.py             # REST endpoints, publishes event on confirmation
│       ├── publisher.py         # pika RabbitMQ publisher
│       └── management/
│           └── commands/
│               └── seed_data.py # seeds 3 movies + showtimes
├── notification_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── notification/
│       ├── settings.py
│       ├── consumer.py          # pika RabbitMQ consumer, retry loop on startup
│       ├── email_sender.py      # sends via Django's EMAIL_BACKEND (SMTP to Mailhog)
│       └── ticket_generator.py  # generates PDF with reportlab, saves to /tickets volume
├── web_app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── webapp/
│       ├── settings.py
│       ├── urls.py
│       ├── views.py
│       └── templates/
│           ├── base.html
│           ├── movies.html
│           ├── seats.html
│           ├── checkout.html
│           └── confirmation.html
├── docker-compose.yml
├── .env.example
└── README.md
Models (reservation_service):

Movie: id, title, duration, genre, format (IMAX/VF/VO)
Showtime: id, movie FK, datetime, hall
Seat: id, showtime FK, seat_number, is_taken
Reservation: id, user_id, showtime FK, created_at, status (pending/confirmed/cancelled)
Ticket: id, reservation FK, pdf_path (local file path), generated_at
Payment: id, reservation FK, amount, currency (MAD), status

Auth: JWT via djangorestframework-simplejwt. Gateway validates token on every request. Two roles: admin and client.
RabbitMQ flow: On reservation confirmed → reservation_service publishes to queue reservation_confirmed → notification_service consumer picks it up → generates PDF ticket with reportlab → saves to shared /tickets Docker volume → sends email via SMTP to Mailhog.
docker-compose.yml must include:

db — postgres:15 with named volume
rabbitmq — rabbitmq:3-management, port 15672 for management UI
mailhog — mailhog/mailhog, port 8025 for web UI to view emails
gateway — port 8000
reservation_service — port 8001
notification_service — port 8002, runs consumer via separate entrypoint
web_app — port 3000
All on cinebook_network bridge
Shared volume tickets_data mounted in both reservation_service and notification_service
healthchecks on db and rabbitmq so dependent services wait

.env.example:
POSTGRES_DB=cinebook
POSTGRES_USER=cinebook_user
POSTGRES_PASSWORD=changeme
POSTGRES_HOST=db
POSTGRES_PORT=5432

RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=reservation_confirmed

EMAIL_HOST=mailhog
EMAIL_PORT=1025
EMAIL_FROM=noreply@cinebook.local

JWT_SECRET_KEY=change_this_to_a_long_random_string
GATEWAY_URL=http://gateway:8000
TICKETS_DIR=/tickets
Additional requirements:

All settings read from environment variables via os.environ
notification_service consumer retries RabbitMQ connection with time.sleep(5) loop until ready
ticket_generator.py saves PDFs to TICKETS_DIR env var path, filename pattern ticket_{reservation_id}.pdf
email_sender.py uses Django's send_mail with EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
seed_data.py management command creates 3 movies with 2 showtimes each and 40 seats per showtime
README with: clone → copy .env.example to .env → docker compose up --build → visit localhost:3000, RabbitMQ UI at localhost:15672, emails at localhost:8025
