# from unittest.mock import patch
# from django.test import TestCase, override_settings
# from django.core.cache import cache
# from django.contrib.auth.models import AnonymousUser
# from .models import Category, Document

# from rest_framework.test import APIClient, APIRequestFactory, APITestCase
# from rest_framework import status
# from rest_framework.throttling import AnonRateThrottle

# # @override_settings(ELASTICSEARCH_DSL_AUTOSYNC=False)
# # class DocumentModelTest(TestCase):
# #     def setUp(self):
# #         # Turn off Celery tasks during tests to avoid side effects
# #         patcher = patch("documents_app.signals.index_document_task.delay")
# #         self.mock_index_task = patcher.start()
# #         self.addCleanup(patcher.stop)

# #         self.category = Category.objects.create(name="Backend", slug="backend")

# #     def test_create_document_with_tags(self):
# #         document = Document.objects.create(
# #             title="Bài viết test",
# #             content="Nội dung test.",
# #             category=self.category,
# #             tags=["django", "test"],
# #             author="Tri",
# #         )

# #         self.assertIsInstance(document.tags, list)
# #         self.assertEqual(document.tags, ["django", "test"])

# #     def test_created_at_is_set_automatically(self):
# #         document = Document.objects.create(
# #             title="Bài viết test 2",
# #             content="Nội dung test.",
# #             category=self.category,
# #             author="Tri",
# #         )

# #         self.assertIsNotNone(document.created_at)
# #         self.assertIsNotNone(document.updated_at)

# #     def test_default_values(self):
# #         document = Document.objects.create(
# #             title="Bài viết test 3",
# #             content="Nội dung test.",
# #             category=self.category,
# #             author="Tri",
# #         )

# #         self.assertTrue(document.is_published)
# #         self.assertEqual(document.view_count, 0)
# #         self.assertEqual(document.tags, [])



# class SearchTest(APITestCase):
    
#     def setUp(self):
#         self.url = "/api/search/?q=django"
#         self.reset_throttle()  # Reset throttle before each test
    
#     def reset_throttle(self):
#         factory = APIRequestFactory()
#         request = factory.get(self.url)
#         request.user = AnonymousUser()
#         print("throttle for request:", request)
#         throttle = AnonRateThrottle()
#         key = throttle.get_cache_key(request, None)
#         print("Resetting throttle key:", key)
        
#         if key:
#             cache.delete(key) 
        
#     def test_search_returns_429_when_rate_limit_exceeded(self):
#         print("Running test_rate_limiting_search...")
#         for _ in range(10):
#             response = self.client.get(self.url)
#             print("Response status code for request:", response.status_code)
#             self.assertEqual(response.status_code, status.HTTP_200_OK)

#         # request 11th
#         response = self.client.get(self.url)
#         print("Response status code for 11th request:", response.status_code, response.content)
#         self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)