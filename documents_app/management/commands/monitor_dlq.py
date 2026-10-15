from django.conf import settings
from django.core.management.base import BaseCommand
from kombu import Connection

from documents_app.messaging.dlq import DEAD_LETTER_QUEUE, extract_task_details


class Command(BaseCommand):
    help = "Inspect messages in celery.dlq without removing them."

    def handle(self, *args, **options):
        messages = []
        with Connection(settings.CELERY_BROKER_URL) as connection:
            queue = DEAD_LETTER_QUEUE(connection)
            queue.declare()
            while message := queue.get(no_ack=False):
                messages.append(message)

            if not messages:
                self.stdout.write("celery.dlq is empty.")
                return

            self.stdout.write("message_id | document_id | error | retry_count | timestamp")
            for message in messages:
                details = extract_task_details(message)
                self.stdout.write(
                    "{message_id} | {document_id} | {error} | {retry_count} | {timestamp}".format(**details)
                )

            # basic_get is required to inspect messages. Requeue every message
            # afterwards so this command is read-only from an operator's view.
            for message in messages:
                message.reject(requeue=True)
