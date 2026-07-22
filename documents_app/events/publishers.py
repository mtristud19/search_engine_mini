import json
from django.core.cache import cache
from .constants import DocumentEvents

class DocumentPublishers():
    
    def __init__(self):
        self.redis = cache.client.get_client()
    
    def created(self, instance):

        self.redis.publish(
            DocumentEvents.CREATED,
            json.dumps({
                "id": str(instance.id),
                "title": instance.title,
            }),
        )
    