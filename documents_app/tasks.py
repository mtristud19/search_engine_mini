from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def index_document_task(self, document_id):
    """Lấy document từ Postgres và ghi vào Elasticsearch."""
    from .models import Document
    from .documents import DocumentIndex

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
    """Xóa document khỏi Elasticsearch khi bị xóa ở Postgres."""
    from .documents import DocumentIndex

    try:
        DocumentIndex().get(id=document_id).delete()
    except Exception:
        # Document có thể đã không còn trong index — bỏ qua
        pass
