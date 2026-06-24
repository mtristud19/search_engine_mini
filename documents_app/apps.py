from django.apps import AppConfig


class DocumentsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents_app'

    def ready(self):
        # Import signals to ensure they are registered
        import documents_app.signals