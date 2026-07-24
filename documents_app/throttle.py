import math
import time
import uuid

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

from .utils import get_client_ip


SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local request_id = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now_ms - window_ms)

local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    return {0, tonumber(oldest[2]) + window_ms - now_ms}
end

redis.call('ZADD', key, now_ms, request_id)
redis.call('PEXPIRE', key, window_ms)
return {1, 0}
"""



class SlidingWindowThrottle(BaseThrottle):
    """Limit each client IP to ``LIMIT`` requests during a rolling window."""

    LIMIT = 10
    WINDOW = 60  # seconds
    cache_key_prefix = "rate_limit:search"

    def __init__(self):
        self.redis = cache.client.get_client()
        self.wait_duration = None

    def allow_request(self, request, view):
        ip = get_client_ip(request) or "unknown"
        cache_key = f"{self.cache_key_prefix}:{ip}"
        now_ms = time.time_ns() // 1_000_000

        allowed, retry_after_ms = self.redis.eval(
            SLIDING_WINDOW_SCRIPT,
            1,
            cache_key,
            now_ms,
            self.WINDOW * 1_000,
            self.LIMIT,
            uuid.uuid4().hex,
        )

        if allowed:
            return True

        self.wait_duration = max(1, math.ceil(retry_after_ms / 1_000))
        return False

    def wait(self):
        """Return seconds until the oldest request leaves the rolling window."""
        return self.wait_duration