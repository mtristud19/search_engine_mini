from documents_app.messaging.rabbitmq import publish_document_event
from .constants import DocumentEvents
import json

class DocumentPublishers:
    
    def publish(self, instance, event):
        print(f"@@@Publishers: Publishing event {event} with document {instance}..."    )
        publish_document_event(
            event,
            {
                "id": str(instance.id),
                "title": instance.title,
            },
        )
