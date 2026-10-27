import secrets
from collections import defaultdict, deque
from threading import Lock
from time import monotonic, time

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.errors import AppError

_redis_client: Redis | None = None
_redis_failed = False


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    # Assumes the API is reachable only through Nginx, which sets
    # X-Forwarded-For to $remote_addr rather than appending the client value.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_redis() -> Redis | None:
    from app.core.config import get_settings

    global _redis_client, _redis_failed
    url = get_settings().redis_url
    if not url:
        return None
    if _redis_client is None and not _redis_failed:
        try:
            _redis_client = Redis.from_url(url, decode_responses=True)
        except RedisError:
            _redis_failed = True
            return None
    return _redis_client


def redis_ready() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except RedisError:
        return False


def _redis_allow(client: Redis, key: str, limit: int, window_seconds: float) -> bool:
    now = time()
    member = f"{now:.6f}:{secrets.token_hex(4)}"
    cutoff = now - window_seconds
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", cutoff)
    pipe.zadd(key, {member: now})
    pipe.zcard(key)
    pipe.expire(key, int(window_seconds) + 1)
    _, _, count, _ = pipe.execute()
    if int(count) > limit:
        client.zrem(key, member)
        return False
    return True


def enforce_rate_limit(request: Request, scope: str, limit: int) -> None:
    from app.core.config import get_settings

    if not get_settings().rate_limit_enabled:
        return
    key = f"{scope}:{client_ip(request)}"
    client = get_redis()
    allowed = True
    if client is not None:
        try:
            allowed = _redis_allow(client, key, limit, 60)
        except RedisError:
            allowed = limiter.allow(key, limit, 60)
    else:
        allowed = limiter.allow(key, limit, 60)
    if not allowed:
        raise AppError(429, "Too many requests. Please try again shortly.")
