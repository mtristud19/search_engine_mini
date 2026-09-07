from documents_app.messaging.rabbitmq import publish_document_event
from .constants import DocumentEvents


class DocumentPublishers:
    
    def created(self, instance):
        publish_document_event(
            DocumentEvents.CREATED,
            {
                "id": str(instance.id),
                "title": instance.title,
            },
        )
