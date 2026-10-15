"""Definitions shared by the Dead Letter Queue management commands."""

from kombu import Exchange, Queue


TASK_EXCHANGE = Exchange("document_tasks", type="direct", durable=True)
DEAD_LETTER_EXCHANGE = Exchange("dlx", type="direct", durable=True)
DEAD_LETTER_QUEUE = Queue(
    "celery.dlq",
    DEAD_LETTER_EXCHANGE,
    routing_key="celery.dead",
    durable=True,
)


def extract_task_details(message):
    """Return the useful Celery and RabbitMQ metadata from a DLQ message."""
    headers = message.headers or {}
    payload = message.payload
    args = payload[0] if isinstance(payload, list) and payload else []
    document_id = args[0] if args else None
    deaths = headers.get("x-death", [])
    latest_death = deaths[0] if deaths else {}

    return {
        "message_id": headers.get("id"),
        "document_id": document_id,
        "error": headers.get("x-last-error", "Unknown error"),
        "retry_count": headers.get("retries", 0),
        "timestamp": headers.get("x-last-error-at") or latest_death.get("time"),
        "x_death": deaths,
    }
