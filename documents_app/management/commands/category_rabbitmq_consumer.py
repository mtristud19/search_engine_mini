import json

from django.core.management.base import BaseCommand

from documents_app.messaging.rabbitmq import DOCUMENT_RABBITMQ_CONSUMER_QUEUE, consume_document_events


class Command(BaseCommand):
    help = "Consume RabbitMQ document events and print to the terminal."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Listening on RabbitMQ queue: {DOCUMENT_RABBITMQ_CONSUMER_QUEUE}"))
        self.stdout.write("Press Ctrl+C to stop.")

        def handle_document_rabbitmq(event):
            self.stdout.write(f"Document event: {json.dumps(event, ensure_ascii=False)}")

        try:
            consume_document_events(DOCUMENT_RABBITMQ_CONSUMER_QUEUE, handle_document_rabbitmq)
        except KeyboardInterrupt:
            self.stdout.write("\nDocument RabbitMQ consumer stopped.")
