import json

from django.core.cache import cache
from django.core.management.base import BaseCommand
from documents_app.events.subscriber import DocumentSubscriber
from documents_app.events.constants import DocumentEvents


DEFAULT_CHANNEL = DocumentEvents.CREATED


class Command(BaseCommand):
    help = "Listen for Redis Pub/Sub events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel",
            default=DEFAULT_CHANNEL,
            help=f"Redis channel to subscribe to (default: {DEFAULT_CHANNEL}).",
        )

    def handle(self, *args, **options):
        channel = options["channel"]
        
        try:
            subscriber = DocumentSubscriber()
            subscriber.start(channel)
        
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Cannot subscribe to Redis channel '{channel}': {exc}"))
            raise exc
       
