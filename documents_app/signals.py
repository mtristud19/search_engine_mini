from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document
from .tasks import index_document_task, delete_document_task


@receiver(post_save, sender=Document)
def document_saved(sender, instance, **kwargs):
    # Đẩy task vào Celery — không index đồng bộ để tránh block request
    index_document_task.delay(str(instance.id))


@receiver(post_delete, sender=Document)
def document_deleted(sender, instance, **kwargs):
    delete_document_task.delay(str(instance.id))
