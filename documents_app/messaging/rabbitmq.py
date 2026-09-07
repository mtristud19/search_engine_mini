"""Durable RabbitMQ fanout messaging for document domain events."""

from socket import timeout as SocketTimeout

from django.conf import settings
from kombu import Connection, Consumer, Exchange, Producer, Queue


DOCUMENT_EVENTS_EXCHANGE = Exchange("document.events", type="fanout", durable=True)
LOG_CONSUMER_QUEUE = "log_consumer"
NOTIFY_CONSUMER_QUEUE = "notify_consumer"


def _event_queue(queue_name):
    """Return a durable queue with its own binding to the fanout exchange."""
    return Queue(
        queue_name,
        exchange=DOCUMENT_EVENTS_EXCHANGE,
        routing_key="",
        durable=True,
        auto_delete=False,
    )


def publish_document_event(event_type, payload):
    """Publish one persistent document event to every bound consumer queue."""
    event = {"event_type": str(event_type), **payload}
    with Connection(settings.CELERY_BROKER_URL) as connection:
        with Producer(connection) as producer:
            producer.publish(
                event,
                exchange=DOCUMENT_EVENTS_EXCHANGE,
                routing_key="",
                serializer="json",
                delivery_mode="persistent",
                declare=[DOCUMENT_EVENTS_EXCHANGE],
            )


def consume_document_events(queue_name, callback):
    """Block while consuming and acknowledging events from one durable queue."""
    queue = _event_queue(queue_name)
    with Connection(settings.CELERY_BROKER_URL) as connection:
        # Declare before consuming so the exchange, queue, and binding are all
        # visible in Management UI and messages persist while this consumer is down.
        queue.maybe_bind(connection)
        queue.declare()

        def handle_event(body, message):
            try:
                callback(body)
            except Exception:
                # Keep the event for a later retry if the consumer action fails.
                message.reject(requeue=True)
                raise
            else:
                message.ack()

        with Consumer(connection, queues=[queue], callbacks=[handle_event], accept=["json"]):
            while True:
                try:
                    connection.drain_events(timeout=1)
                except SocketTimeout:
                    # A short timeout gives Ctrl+C a predictable way to stop the command.
                    continue
