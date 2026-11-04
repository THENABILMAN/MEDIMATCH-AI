"""In-process sliding window rate limits.

Counts are per worker, so a multi-worker deployment allows up to workers x limit. A shared store
such as Redis is the next step if that stops being enough.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.schemas.profile import UserMeResponse

WINDOW_SECONDS = 60
MAX_TRACKED_KEYS = 100_000


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(self, key: str, limit: int) -> None:
        """Records a hit, or raises 429 if the caller is over the limit."""
        if not settings.RATE_LIMIT_ENABLED:
            return

        now = time.monotonic()
        with self._lock:
            if len(self._hits) > MAX_TRACKED_KEYS:
                self._hits.clear()

            hits = self._hits[key]
            while hits and hits[0] <= now - WINDOW_SECONDS:
                hits.popleft()

            if len(hits) >= limit:
                retry_after = int(hits[0] + WINDOW_SECONDS - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


limiter = SlidingWindowLimiter()


def limit_by_ip(scope: str, setting: str) -> Callable[[Request], None]:
    """Limits anonymous routes. `setting` names the Settings field so limits stay configurable."""

    def check(request: Request) -> None:
        host = request.client.host if request.client else "unknown"
        limiter.check(f"{scope}:{host}", getattr(settings, setting))

    return check


def limit_by_user(scope: str, setting: str) -> Callable[[UserMeResponse], None]:
    def check(current_user: UserMeResponse = Depends(get_current_user)) -> None:
        limiter.check(f"{scope}:{current_user.id}", getattr(settings, setting))

    return check
