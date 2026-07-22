import json
from django.core.cache import cache

class DocumentSubscriber:
    
    def __init__(self):
        self.redis = cache.client.get_client()
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        
    def start(self, channel):
        
        print(f"Listening on Redis channel: {channel}")
        self.pubsub.subscribe(channel)
        
        print("Press Ctrl+C to stop.")
        
        try:
            for event in self.pubsub.listen():
                self.handle_event(event)
                
        except KeyboardInterrupt:
            print("\nListener stopped.")
        finally:
            self.pubsub.close()
        
    def handle_event(self, event):
        """Process one Redis event.

        ``event`` contains Redis metadata such as ``channel`` and ``data``.
        JSON payloads are decoded automatically; non-JSON payloads remain strings.
        """
        
        payload = event["data"]
        
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        try:
            payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            pass

        print(f"Received event: {payload}")