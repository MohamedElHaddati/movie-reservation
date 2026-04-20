# CineBook

CineBook is a self-hosted movie ticket reservation system built as event-driven microservices with Django, PostgreSQL, RabbitMQ, and Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Setup

1. Clone this repository.
2. Copy environment variables:
   - `cp .env.example .env` (Linux/macOS)
   - `copy .env.example .env` (Windows)
3. Start the stack:
   - `docker compose up --build`
4. Seed initial data:
   - `docker compose exec reservation_service python manage.py seed_data`

## URLs

| Service | URL |
|---|---|
| Web app | http://localhost:3000 |
| RabbitMQ UI | http://localhost:15672 |
| Mailhog inbox | http://localhost:8025 |
