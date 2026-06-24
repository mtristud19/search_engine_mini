import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'search_engine_mini.settings')

app = Celery('search_engine_mini')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
