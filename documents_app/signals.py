from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document
from .tasks import index_document_task, delete_document_task, invalidate_cache_document, publish_document
from .events.constants import DocumentEvents


@receiver(post_save, sender=Document)
def document_saved(sender, instance, created, **kwargs):
    
    category_slug = instance.category.slug if instance.category else "uncategorized"
    
    index_document_task.delay(str(instance.id))
    invalidate_cache_document(str(instance.id))
    
    if created:
        publish_document.delay(str(instance.id), DocumentEvents.CREATED + f".{str(category_slug)}")
    else:
        publish_document.delay(str(instance.id), DocumentEvents.UPDATED + f".{str(category_slug)}")


@receiver(post_delete, sender=Document)
def document_deleted(sender, instance, **kwargs):
    
    category_slug = instance.category.slug if instance.category else "uncategorized"
    
    delete_document_task.delay(str(instance.id))
    invalidate_cache_document(str(instance.id))
    publish_document.delay(str(instance.id), DocumentEvents.DELETED + f".{str(category_slug)}")
