# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
from pydantic import BaseModel, ConfigDict, Field, field_validator

# FAULT SPECS --------------------------------------------------------------------------------------------------------------------------------------|
class _Spec(BaseModel):
    model_config = ConfigDict(frozen = True, extra = "forbid")

# Delay forwarding by delay_ms plus a random amount between 0 and jitter_ms.
class LatencyFault(_Spec):
    delay_ms: float = Field(ge = 0)
    jitter_ms: float = Field(default = 0.0, ge = 0)
    probability: float = Field(default = 1.0, ge = 0, le = 1)

# Close the connection abruptly.
class DropFault(_Spec):
    probility: float = Field(default = 1.0, ge = 0, le = 1)

# Answer with a synthetic 5xx response (hhtp mode only).
class ErrorFault(_Spec):
    status: int = Field(default = 503, ge = 500, le = 599)
    probability: float = Field(deafult = 1.0, ge = 0, le = 1)

# Limit throughput per connection with a token bucket.
class ThrottleFault(_Spec):
    bytes_per_sec: int = Field(gt = 0)
    burst_bytes: int | None = Field(default = None, gt = 0)

    @property
    def effective_burst(self) -> int:
        return self.bytes_per_sec if self.burst_bytes is None else self.burst_bytes

# MATCHING -----------------------------------------------------------------------------------------------------------------------------------------|
class Match(_Spec):
    methods: frozenset[str] = frozenset()
    path_prefix: str = ""

    @field_validator("methods")
    @classmethod
    def _uppercase_methods(cls, value: frozenset[str]) -> frozenset[str]:
        return frozenset(method.upper() for method in value)

    @property
    def is_catch_all(self) -> bool:
        return not self.methods and not self.path_prefix

    def matches(self, method: str, path: str) -> bool:
        if self.methods and method.upper() not in self.methods:
            return False

        return path.startswith(self.path_prefix)

# PROFILE ------------------------------------------------------------------------------------------------------------------------------------------|
class FaultRule(_Spec):
    name: str = ""
    match: Match = Field(default_factory = Match)
    latency: LatencyFault | None = None
    drop: DropFault | None = None
    error: ErrorFault | None = None
    throttle: ThrottleFault | None = None

class FaultProfile(_Spec):
    seed: int = 0
    rules: tuple[FaultRule, ...] = ()
