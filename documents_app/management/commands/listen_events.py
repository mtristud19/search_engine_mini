from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deprecated: use log_consumer or notify_consumer."

    def handle(self, *args, **options):
        raise CommandError("Redis Pub/Sub was replaced. Use log_consumer or notify_consumer.")
