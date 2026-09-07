import json

from django.conf import settings
from django.core.management.base import BaseCommand

from documents_app.messaging.rabbitmq import LOG_CONSUMER_QUEUE, consume_document_events


class Command(BaseCommand):
    help = "Consume document events and append them to document_events.log."

    def handle(self, *args, **options):
        log_path = settings.BASE_DIR / "logs" / "document_events.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f"Listening on RabbitMQ queue: {LOG_CONSUMER_QUEUE}"))
        self.stdout.write(f"Writing events to: {log_path}")
        self.stdout.write("Press Ctrl+C to stop.")

        def write_event(event):
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            self.stdout.write(f"Logged event: {event}")

        try:
            consume_document_events(LOG_CONSUMER_QUEUE, write_event)
        except KeyboardInterrupt:
            self.stdout.write("\nLog consumer stopped.")
