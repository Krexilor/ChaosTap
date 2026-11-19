# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import random
from dataclasses import dataclass

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.faults.models import FaultProfile, FaultRule

# TYPES --------------------------------------------------------------------------------------------------------------------------------------------|
@dataclass(frozen = True, slots = True)
class RequestInfo:
    method: str
    path: str

@dataclass(frozen = True, slots = True)
class Decision:
    delay_s: float = 0.0
    drop: bool = False
    error_status: int | None = None
    rate_bytes_per_s: int | None = None
    burst_bytes: int | None = None
    rule_index: int | None = None

# CONNECTION FAULTS --------------------------------------------------------------------------------------------------------------------------------|
class ConnectionFaults:
    def __init__(self, profile: FaultProfile, conn_id: int) -> None:
        self._profile = profile
        self._rng = random.Random(f"{profile.seed}:{conn_id}")

    def decide(self, request: RequestInfo | None = None) -> Decision:
        for index, rule in enumerate(self._profile.rules):
            if self._matches(rule, request):
                return self._evaluate(index, rule)

        return Decision()

    @staticmethod
    def _matches(rule: FaultRule, request: RequestInfo | None) -> bool:
        if request is None:
            return rule.match.is_catch_all

        return rule.match.matches(request.method, request.path)

    def _chance(self, probability: float) -> bool:
        return self._rng.random() < probability

    def _evaluate(self, index: int, rule: FaultRule) -> Decision:
        delay_s = 0.0
        drop = False
        error_status: int | None = None
        rate: int | None = None
        burst: int | None = None

        if rule.latency is not None:
            fires = self._chance(rule.latency.probability)
            jitter_ms = self._rng.uniform(0.0, rule.latency.jitter_ms)

            if fires:
                delay_s = (rule.latency.delay_ms + jitter_ms) / 1000.0

        if rule.drop is not None:
            drop = self._chance(rule.drop.probability)

        if rule.error is not None:
            fires = self._chance(rule.error.probability)

            if fires and not drop:
                error_status = rule.error.status

        if rule.throttle is not None:
            rate = rule.throttle.bytes_per_sec
            burst = rule.throttle.effective_burst

        return Decision(
            delay_s = delay_s,
            drop = drop,
            error_status = error_status,
            rate_bytes_per_s = rate,
            burst_bytes = burst,
            rule_index = index
        )

# ENGINE -------------------------------------------------------------------------------------------------------------------------------------------|
class FaultEngine:
    def __init__(self, profile: FaultProfile | None = None) -> None:
        self._profile = profile if profile is not None else FaultProfile()

    @property
    def profile(self) -> FaultProfile:
        return self._profile

    def replace(self, profile: FaultProfile) -> None:
        self._profile = profile

    def for_connection(self, conn_id: int) -> ConnectionFaults:
        return ConnectionFaults(self._profile, conn_id)
