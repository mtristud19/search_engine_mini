import os
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'search_engine_mini.settings')

app = Celery('search_engine_mini')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@worker_ready.connect
def declare_dead_letter_topology(**kwargs):
    """Create the durable DLQ binding before this worker starts processing."""
    from django.conf import settings
    from kombu import Connection
    from documents_app.messaging.dlq import DEAD_LETTER_QUEUE

    with Connection(settings.CELERY_BROKER_URL) as connection:
        DEAD_LETTER_QUEUE(connection).declare()
