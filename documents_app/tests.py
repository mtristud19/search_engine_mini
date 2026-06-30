from unittest.mock import patch
from django.test import TestCase, override_settings
from .models import Category, Document

@override_settings(ELASTICSEARCH_DSL_AUTOSYNC=False)
class DocumentModelTest(TestCase):
    def setUp(self):
        # Turn off Celery tasks during tests to avoid side effects
        patcher = patch("documents_app.signals.index_document_task.delay")
        self.mock_index_task = patcher.start()
        self.addCleanup(patcher.stop)

        self.category = Category.objects.create(name="Backend", slug="backend")

    def test_create_document_with_tags(self):
        document = Document.objects.create(
            title="Bài viết test",
            content="Nội dung test.",
            category=self.category,
            tags=["django", "test"],
            author="Tri",
        )

        self.assertIsInstance(document.tags, list)
        self.assertEqual(document.tags, ["django", "test"])

    def test_created_at_is_set_automatically(self):
        document = Document.objects.create(
            title="Bài viết test 2",
            content="Nội dung test.",
            category=self.category,
            author="Tri",
        )

        self.assertIsNotNone(document.created_at)
        self.assertIsNotNone(document.updated_at)

    def test_default_values(self):
        document = Document.objects.create(
            title="Bài viết test 3",
            content="Nội dung test.",
            category=self.category,
            author="Tri",
        )

        self.assertTrue(document.is_published)
        self.assertEqual(document.view_count, 0)
        self.assertEqual(document.tags, [])