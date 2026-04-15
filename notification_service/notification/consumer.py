import json
import os
import time

import django
import pika
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification.settings')
django.setup()

from notification.email_sender import send_ticket_email
from notification.ticket_generator import generate_ticket_pdf


def callback(ch, method, _properties, body):
    payload = json.loads(body)
    reservation_id = payload['reservation_id']
    recipient = payload.get('user_email', 'client@cinebook.local')

    pdf_path = generate_ticket_pdf(reservation_id, payload)
    send_ticket_email(recipient, reservation_id, pdf_path)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def consume_forever():
    while True:
        try:
            credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
            params = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=settings.RABBITMQ_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=settings.RABBITMQ_QUEUE, on_message_callback=callback)
            print('notification_service consumer started')
            channel.start_consuming()
        except Exception as exc:
            print(f'RabbitMQ not ready ({exc}), retrying in 5 seconds...')
            time.sleep(5)


if __name__ == '__main__':
    consume_forever()
