# Cinebook - Movie Reservation Microservices

Self-hosted movie ticket reservation system built with Django microservices, PostgreSQL, RabbitMQ, Mailhog, and Docker Compose.

## Services
- `gateway` (port `8000`) - validates JWT and proxies traffic
- `reservation_service` (port `8001`) - movies/showtimes/seats/reservations API
- `notification_service` (port `8002`) - RabbitMQ consumer, PDF generation, email sending
- `web_app` (port `3000`) - user web interface
- `db` - PostgreSQL 15
- `rabbitmq` - queue + management UI (`http://localhost:15672`)
- `mailhog` - email inbox UI (`http://localhost:8025`)

## Quick start
1. Clone repository.
2. Copy environment template:
   ```bash
   cp .env.example .env
   ```
3. Start stack:
   ```bash
   docker compose up --build
   ```
4. Open app at `http://localhost:3000`.
5. Open RabbitMQ UI at `http://localhost:15672`.
6. Open Mailhog UI at `http://localhost:8025`.

## Notes
- Ticket PDFs are saved in shared Docker volume mounted at `/tickets`.
- Queue used for reservation confirmation events: `reservation_confirmed`.
- JWT token must contain a `role` claim (`admin` or `client`) for gateway authorization.
