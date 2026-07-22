from celery import shared_task
from django.core.cache import cache
from documents_app.events.publishers import DocumentPublishers
from .models import Document
from .documents import DocumentIndex

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def index_document_task(self, document_id):

    # print(f"Indexing document {document_id} in Elasticsearch...")

    try:
        document = Document.objects.select_related("category").get(id=document_id)
    except Document.DoesNotExist:
        return

    try:
        DocumentIndex().update(document)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def delete_document_task(document_id):
    """Delete document in Elasticsearch when deleted in Postgres."""
    

    try:
        DocumentIndex().get(id=document_id).delete()
    except Exception:
        pass

def invalidate_cache_document(document_id):
    """ 
    Read the tracking set of document_id, delete all cache_keys in it,
    then delete the tracking set as well.
    """
    # print(f"Invalidating cache for document {document_id}...")
    
    redis_client = cache.client.get_client()
    tracking_key = f"search:tracking:{document_id}"

    # smembers returns an empty set if the key does not exist — no need to check None.
    raw_keys = redis_client.smembers(tracking_key)
    # print(f"Found {raw_keys} cache keys to invalidate for document {document_id}.")
    if raw_keys:
        cache_keys = [key.decode() for key in raw_keys]
        cache.delete_many(cache_keys)
        redis_client.delete(tracking_key)
 
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def publish_document(self, document_id):
    
    try:
        instance = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return
    
    try:
        publisher = DocumentPublishers()
        publisher.created(instance)
    except Exception as exc:
        raise self.retry(exc=exc)