from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from rest_framework.test import APITestCase, APIRequestFactory


class ThrottleTestMixin:

    def reset_throttle(self, throttle_class, url, user=None):
        request = APIRequestFactory().get(url)
        request.user = user or AnonymousUser()

        key = throttle_class().get_cache_key(request, None)
        
        if key:
            cache.delete(key)


class BaseAPITestCase(APITestCase):
    """
    Common setup for API tests.
    """
    pass