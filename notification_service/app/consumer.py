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
    try:
        payload = json.loads(body.decode("utf-8"))
        reservation_id = payload["reservation_id"]

        reservation = (
            Reservation.objects.select_related("showtime__movie", "user")
            .prefetch_related("seats")
            .get(id=reservation_id)
        )
        ticket_path = ticket_generator.generate(reservation)
        email_sender.send(reservation, ticket_path)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Processed reservation %s", reservation_id)
    except Exception:
        logger.exception("Failed processing message")
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
