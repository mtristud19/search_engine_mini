from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

from documents_app.tests.base import (
    BaseAPITestCase,
    ThrottleTestMixin,
)

class SearchThrottleTest(
    ThrottleTestMixin,
    BaseAPITestCase,
):

    def setUp(self):
        self.url = "/api/search/?q=django"
        self.reset_throttle(
            AnonRateThrottle,
            self.url,
        )

    def test_search_returns_429_when_rate_limit_exceeded(self):
        for _ in range(10):
            response = self.client.get(self.url)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
            )
        
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )