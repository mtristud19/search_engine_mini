import json

from django.core.management.base import BaseCommand

from documents_app.messaging.rabbitmq import NOTIFY_CONSUMER_QUEUE, consume_document_events


class Command(BaseCommand):
    help = "Consume document events and print notifications to the terminal."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Listening on RabbitMQ queue: {NOTIFY_CONSUMER_QUEUE}"))
        self.stdout.write("Press Ctrl+C to stop.")

        def notify(event):
            self.stdout.write(f"Document event: {json.dumps(event, ensure_ascii=False)}")

        try:
            consume_document_events(NOTIFY_CONSUMER_QUEUE, notify)
        except KeyboardInterrupt:
            self.stdout.write("\nNotify consumer stopped.")
