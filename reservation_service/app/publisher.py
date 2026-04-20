import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

import pika

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_connection = None
_channel = None


def _connection_params():
    credentials = pika.PlainCredentials(
        os.environ.get("RABBITMQ_USER", "guest"),
        os.environ.get("RABBITMQ_PASSWORD", "guest"),
    )
    return pika.ConnectionParameters(
        host=os.environ.get("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.environ.get("RABBITMQ_PORT", "5672")),
        credentials=credentials,
        heartbeat=60,
    )


def _ensure_channel():
    global _connection, _channel

    with _lock:
        if _connection and _connection.is_open and _channel and _channel.is_open:
            return _channel

        last_error = None
        for attempt in range(1, 6):
            try:
                _connection = pika.BlockingConnection(_connection_params())
                _channel = _connection.channel()
                queue = os.environ.get("RABBITMQ_QUEUE", "reservation_confirmed")
                _channel.queue_declare(queue=queue, durable=True)
                return _channel
            except Exception as exc:
                last_error = exc
                logger.warning("RabbitMQ connection attempt %s failed: %s", attempt, exc)
                time.sleep(2)

        raise RuntimeError(f"Unable to connect to RabbitMQ: {last_error}")


def publish_reservation_confirmed(reservation_id):
    channel = _ensure_channel()
    queue = os.environ.get("RABBITMQ_QUEUE", "reservation_confirmed")
    payload = {
        "reservation_id": reservation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )
