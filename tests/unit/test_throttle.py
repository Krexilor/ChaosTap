# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import pytest

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.proxy.throttle import TokenBucket

# FAKE TIME ----------------------------------------------------------------------------------------------------------------------------------------|
class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay

def _bucket(fake: FakeTime, rate: float = 100, burst: float | None = 100) -> TokenBucket:
    return TokenBucket(rate, burst, clock = fake.clock, sleep = fake.sleep)

# CONSUMING ----------------------------------------------------------------------------------------------------------------------------------------|
async def test_burst_is_available_immediately() -> None:
    fake = FakeTime()
    await _bucket(fake).consume(100)
    assert fake.sleeps == []

async def test_exceeding_the_burst_waits_for_the_deficit() -> None:
    fake = FakeTime()
    bucket = _bucket(fake)
    await bucket.consume(100)
    await bucket.consume(50)
    assert fake.sleeps == [pytest.approx(0.5)]

async def test_tokens_refill_over_time() -> None:
    fake = FakeTime()
    bucket = _bucket(fake)
    await bucket.consume(100)
    fake.now += 0.5
    await bucket.consume(50)
    assert fake.sleeps == []

async def test_refill_is_capped_at_the_burst_size() -> None:
    fake = FakeTime()
    bucket = _bucket(fake)
    await bucket.consume(100)
    fake.now += 60
    await bucket.consume(100)
    await bucket.consume(1)
    assert fake.sleeps == [pytest.approx(0.01)]

async def test_chunk_larger_than_the_burst_waits_for_the_excess() -> None:
    fake = FakeTime()
    await _bucket(fake, rate = 100, burst = 10).consume(110)
    assert fake.sleeps == [pytest.approx(1.0)]

async def test_sustained_throughput_matches_the_rate() -> None:
    fake = FakeTime()
    bucket = _bucket(fake)
    
    for _ in range(10):
        await bucket.consume(100)
        
    assert fake.now == pytest.approx(9.0)

async def test_zero_bytes_never_waits() -> None:
    fake = FakeTime()
    await _bucket(fake).consume(0)
    assert fake.sleeps == []

# CONFIGURATION ------------------------------------------------------------------------------------------------------------------------------------|
def test_burst_defaults_to_the_rate() -> None:
    bucket = TokenBucket(250)
    assert bucket.rate == 250
    assert bucket.capacity == 250

@pytest.mark.parametrize(("rate", "burst"), [(0, None), (-1, None), (100, 0), (100, -5)])
def test_non_positive_limits_are_rejected(rate: float, burst: float | None) -> None:
    with pytest.raises(ValueError, match = "must be positive"):
        TokenBucket(rate, burst)

async def test_negative_chunk_is_rejected() -> None:
    with pytest.raises(ValueError, match = "non-negative"):
        await TokenBucket(100).consume(-1)

async def test_default_clock_and_sleep_work() -> None:
    await TokenBucket(1_000_000).consume(10)
