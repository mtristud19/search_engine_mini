from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from kombu import Connection, Producer

from documents_app.messaging.dlq import DEAD_LETTER_QUEUE, TASK_EXCHANGE, extract_task_details


class Command(BaseCommand):
    help = "Republish one Celery message from celery.dlq to high_priority."

    def add_arguments(self, parser):
        parser.add_argument("--id", required=True, help="Celery task message_id shown by monitor_dlq.")

    def handle(self, *args, **options):
        requested_id = options["id"]
        held_messages = []
        target = None

        with Connection(settings.CELERY_BROKER_URL) as connection:
            queue = DEAD_LETTER_QUEUE(connection)
            queue.declare()
            while message := queue.get(no_ack=False):
                if extract_task_details(message)["message_id"] == requested_id:
                    target = message
                    break
                held_messages.append(message)

            try:
                if target is None:
                    raise CommandError(f"No DLQ message found with id={requested_id}.")

                # Reset Celery's retry counter: this is an operator-requested
                # retry, not another automatic retry of the exhausted task.
                headers = dict(target.headers or {})
                headers["retries"] = 0
                headers["x-retried-from-dlq"] = requested_id
                headers.pop("x-last-error", None)
                headers.pop("x-last-error-at", None)

                with Producer(connection) as producer:
                    producer.publish(
                        target.body,
                        exchange=TASK_EXCHANGE,
                        routing_key="high_priority",
                        headers=headers,
                        content_type=target.content_type,
                        content_encoding=target.content_encoding,
                        delivery_mode="persistent",
                        declare=[TASK_EXCHANGE],
                    )
                target.ack()
                self.stdout.write(self.style.SUCCESS(
                    f"Republished {requested_id} to high_priority and acknowledged its DLQ copy."
                ))
            finally:
                # Messages examined before the target must remain in the DLQ.
                for message in held_messages:
                    message.reject(requeue=True)
