import json

from documents_app.messaging.rabbitmq import consume_document_events


class DocumentSubscriber:
    """Compatibility wrapper for RabbitMQ document event consumers."""

    def start(self, queue_name):
        print(f"Listening on RabbitMQ queue: {queue_name}")
        print("Press Ctrl+C to stop.")
        try:
            consume_document_events(queue_name, self.handle_event)
        except KeyboardInterrupt:
            print("\nListener stopped.")

    def handle_event(self, event):
        print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
