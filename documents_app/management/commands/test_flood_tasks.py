from django.core.management.base import BaseCommand, CommandError

from documents_app.models import Document
from documents_app.tasks import index_document_task

class Command(BaseCommand):
    help = "Queue low-priority reindex work, then high-priority document indexing work."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=20, help="Tasks to submit to each queue.")

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("--count must be at least 1.")

        document_ids = list(Document.objects.values_list("id", flat=True)[:count])
        if not document_ids:
            raise CommandError("Create at least one Document before flooding tasks.")

        # Re-use documents if there are fewer documents than requested. The
        # Redis lock in the task prevents concurrent indexing of the same one.
        document_ids = [document_ids[index % len(document_ids)] for index in range(count)]

        for document_id in document_ids:
            index_document_task.delay(str(document_id))

        self.stdout.write(self.style.SUCCESS(
            f"Queued {count} low-priority and {count} high-priority tasks."
        ))
