import json
import logging
import os
import time

import django
import pika
from django.conf import settings
from django.db import models

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cinebook_notification.settings")
django.setup()

from app import email_sender, ticket_generator  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
MAX_RETRIES = int(os.environ.get("NOTIFICATION_MAX_RETRIES", "5"))


class Movie(models.Model):
    title = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "app_movie"
        app_label = "app"


class Showtime(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.DO_NOTHING, related_name="+")
    datetime = models.DateTimeField()
    hall = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "app_showtime"
        app_label = "app"


class Seat(models.Model):
    showtime = models.ForeignKey(Showtime, on_delete=models.DO_NOTHING, related_name="+")
    seat_number = models.CharField(max_length=10)
    is_taken = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "app_seat"
        app_label = "app"


class Reservation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name="+")
    showtime = models.ForeignKey(Showtime, on_delete=models.DO_NOTHING, related_name="+")
    created_at = models.DateTimeField()
    status = models.CharField(max_length=20)
    seats = models.ManyToManyField(Seat, related_name="+", db_table="app_reservation_seats")

    class Meta:
        managed = False
        db_table = "app_reservation"
        app_label = "app"


class ReservationSeat(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.DO_NOTHING, db_column="reservation_id", related_name="+")
    seat = models.ForeignKey(Seat, on_delete=models.DO_NOTHING, db_column="seat_id", related_name="+")

    class Meta:
        managed = False
        db_table = "app_reservation_seats"
        app_label = "app"


def _reservation_seats(reservation_id):
    seat_ids = list(
        ReservationSeat.objects.filter(reservation_id=reservation_id).values_list("seat_id", flat=True)
    )
    return list(Seat.objects.filter(id__in=seat_ids))


def _connection():
    credentials = pika.PlainCredentials(
        os.environ.get("RABBITMQ_USER", "guest"),
        os.environ.get("RABBITMQ_PASSWORD", "guest"),
    )
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.environ.get("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.environ.get("RABBITMQ_PORT", "5672")),
            credentials=credentials,
        )
    )


def _process(ch, method, properties, body):
    queue_name = os.environ.get("RABBITMQ_QUEUE", "reservation_confirmed")
    try:
        payload = json.loads(body.decode("utf-8"))
        reservation_id = payload["reservation_id"]

        reservation = (
            Reservation.objects.select_related("showtime__movie", "user")
            .get(id=reservation_id)
        )
        seats = _reservation_seats(reservation_id)
        if not seats:
            raise ValueError(f"Reservation {reservation_id} has no seats")

        ticket_path = ticket_generator.generate(reservation, seats)
        email_sender.send(reservation, ticket_path, seats)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Processed reservation %s", reservation_id)
    except ValueError as exc:
        # Non-retryable validation errors (for example, missing recipient email).
        logger.error("Dropping notification message: %s", exc)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        try:
            current_retry = 0
            if properties and properties.headers:
                current_retry = int(properties.headers.get("x-retry-count", 0))

            if current_retry >= MAX_RETRIES:
                logger.exception(
                    "Dropping message after %s retries (queue=%s, delivery_tag=%s)",
                    current_retry,
                    queue_name,
                    method.delivery_tag,
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            next_retry = current_retry + 1
            headers = dict(properties.headers or {}) if properties and properties.headers else {}
            headers["x-retry-count"] = next_retry
            ch.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers=headers,
                    content_type=getattr(properties, "content_type", None),
                ),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.exception(
                "Failed processing message; requeued for retry %s/%s",
                next_retry,
                MAX_RETRIES,
            )
        except Exception:
            logger.exception("Failed processing message and failed to requeue")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    queue_name = os.environ.get("RABBITMQ_QUEUE", "reservation_confirmed")
    while True:
        try:
            connection = _connection()
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=_process)
            logger.info("Waiting for messages on queue '%s'", queue_name)
            channel.start_consuming()
        except Exception:
            logger.exception("Consumer crashed, retrying in 2s")
            time.sleep(2)


if __name__ == "__main__":
    main()
