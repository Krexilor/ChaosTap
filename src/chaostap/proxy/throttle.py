# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import time
import asyncio
from collections.abc import Awaitable, Callable

# TYPES --------------------------------------------------------------------------------------------------------------------------------------------|
Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]

# TOKEN BUCKET -------------------------------------------------------------------------------------------------------------------------------------|
class TokenBucket:
    def __init__(
        self,
        rate_bytes_per_s: float,
        burst_bytes: float | None = None,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleeper = asyncio.sleep
    ) -> None:
        if rate_bytes_per_s <= 0:
            raise ValueError("rate_bytes_per_s must be positive")

        capacity = rate_bytes_per_s if burst_bytes is None else burst_bytes

        if capacity <= 0:
            raise ValueError("burst_bytes must be positive")

        self._rate = float(rate_bytes_per_s)
        self._capacity = float(capacity)
        self._clock = clock
        self._sleep = sleep
        self._tokens = self._capacity
        self._last = clock()

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def capacity(self) -> float:
        return self._capacity

    async def consume(self, nbytes: int) -> None:
        if nbytes < 0:
            raise ValueError("nbytes must be non-negative")

        self._refill()
        self._tokens -= nbytes

        if self._tokens < 0:
            await self._sleep(-self._tokens / self._rate)

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
