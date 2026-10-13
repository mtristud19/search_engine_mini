from celery import shared_task
from django.core.cache import cache
from redis.exceptions import LockNotOwnedError

from documents_app.events.publishers import DocumentPublishers
from .models import Document
from .documents import DocumentIndex

import logging
logger = logging.getLogger(__name__)
G, Y, R, END = "\033[92m", "\033[93m", "\033[91m", "\033[0m"

# The lock must outlive the slowest expected Elasticsearch indexing operation.
# If it expires first, another worker may acquire the same document lock.
LOCK_TIMEOUT_SECONDS = 60
# A task that loses the lock retries shortly instead of being silently dropped.
LOCK_RETRY_DELAY_SECONDS = 5
# One key per document, so duplicate index tasks for that document cannot overlap.
LOCK_KEY_PREFIX = "lock:document:index"


def _get_document_lock(document_id):
    """Return a non-blocking distributed lock for one document's ES state."""
    return cache.client.get_client().lock(
        f"{LOCK_KEY_PREFIX}:{document_id}",
        timeout=LOCK_TIMEOUT_SECONDS,
        blocking_timeout=0, # Do not keep a Celery worker waiting for an existing lock holder.
        thread_local=False, # The lock can be released safely from this task's execution context.
    )

def _release_lock(lock):
    """Release only when this worker still owns the Redis lock token."""
    try:
        lock.release()
    except LockNotOwnedError:
        # The lock timeout elapsed. Never delete a lock acquired by another worker.
        pass


def _index_document(self, document_id, priority_label):
    lock = _get_document_lock(document_id)
    if not lock.acquire(blocking=False):
        # Another worker is indexing this document. Retry so this task can index
        # the most recent database state after the current worker finishes.
        logger.warning(f"{Y}Skip indexing {document_id}. Another worker owns the lock.")
        raise self.retry(countdown=LOCK_RETRY_DELAY_SECONDS)
    
    logger.info(f"{G}Acquire lock for {priority_label} document index: {document_id}")
    
    try:
        try:
            document = Document.objects.select_related("category").get(id=document_id)
        except Document.DoesNotExist:
            return

        DocumentIndex().update(document)
        
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        # Runs on success, return, and exception; it unblocks the next task.
        _release_lock(lock)


@shared_task(bind=True, max_retries=10, default_retry_delay=10, acks_late=True, reject_on_worker_lost=True)
def index_document_task(self, document_id):
    """Index a document created or updated by a user immediately."""
    return _index_document(self, document_id, "high-priority")

@shared_task(bind=True, max_retries=10, default_retry_delay=10)
def delete_document_task(self, document_id):
    """Delete document in Elasticsearch when deleted in Postgres."""
    lock = _get_document_lock(document_id)
    if not lock.acquire(blocking=False):
        raise self.retry(countdown=LOCK_RETRY_DELAY_SECONDS)

    try:
        DocumentIndex().get(id=document_id).delete()
    except Exception:
        pass
    finally:
        _release_lock(lock)

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
def publish_document(self, document_id, event):
    
    try:
        instance = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return
    
    try:
        publisher = DocumentPublishers()
        publisher.publish(instance, event)
    except Exception as exc:
        raise self.retry(exc=exc)
