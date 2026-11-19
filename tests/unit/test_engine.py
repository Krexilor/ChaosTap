# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import pytest

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.faults.engine import ConnectionFaults, Decision, FaultEngine, RequestInfo
from chaostap.faults.models import DropFault, ErrorFault, FaultProfile, FaultRule, LatencyFault, Match, ThrottleFault

# HELPERS ------------------------------------------------------------------------------------------------------------------------------------------|
GET_ROOT = RequestInfo("GET", "/")

def _profile(*rules: FaultRule, seed: int = 1) -> FaultProfile:
    return FaultProfile(seed = seed, rules = rules)

def _faults(profile: FaultProfile, conn_id: int = 0) -> ConnectionFaults:
    return FaultEngine(profile).for_connection(conn_id)

def _noisy_profile(seed: int = 1) -> FaultProfile:
    rule = FaultRule(
        latency = LatencyFault(delay_ms = 10, jitter_ms = 90, probability = 0.5),
        drop = DropFault(probability = 0.2),
        error = ErrorFault(status = 502, probability = 0.3)
    )
    return _profile(rule, seed = seed)

def _sequence(profile: FaultProfile, conn_id: int, count: int = 50) -> list[Decision]:
    faults = _faults(profile, conn_id)
    return [faults.decide(GET_ROOT) for _ in range(count)]

# BASIC DECISIONS ----------------------------------------------------------------------------------------------------------------------------------|
def test_empty_profile_passes_traffic_through() -> None:
    assert _faults(FaultProfile()).decide(GET_ROOT) == Decision()

def test_fixed_latency() -> None:
    profile = _profile(FaultRule(latency=LatencyFault(delay_ms = 100)))
    decision = _faults(profile).decide(GET_ROOT)
    assert decision.delay_s == pytest.approx(0.1)

def test_jitter_stays_within_bounds() -> None:
    profile = _profile(FaultRule(latency = LatencyFault(delay_ms = 100, jitter_ms = 50)))
    delays = [d.delay_s for d in _sequence(profile, 0, count = 200)]
    assert all(0.1 <= delay <= 0.15 for delay in delays)
    assert len(set(delays)) > 1

def test_probability_zero_never_fires_and_one_always_fires() -> None:
    never = _profile(FaultRule(drop = DropFault(probability = 0.0)))
    always = _profile(FaultRule(drop = DropFault(probability = 1.0)))
    assert not any(d.drop for d in _sequence(never, 0, count = 100))
    assert all(d.drop for d in _sequence(always, 0, count = 100))

def test_probability_is_roughly_respected() -> None:
    profile = _profile(FaultRule(drop = DropFault(probability = 0.5)))
    drops = sum(d.drop for d in _sequence(profile, 0, count = 1000))
    assert 400 <= drops <= 600

def test_error_status_is_reported() -> None:
    profile = _profile(FaultRule(error = ErrorFault(status = 502)))
    assert _faults(profile).decide(GET_ROOT).error_status == 502

def test_drop_takes_precedence_over_error() -> None:
    profile = _profile(FaultRule(drop = DropFault(), error = ErrorFault()))
    decision = _faults(profile).decide(GET_ROOT)
    assert decision.drop
    assert decision.error_status is None

def test_throttle_rate_and_burst() -> None:
    plain = _profile(FaultRule(throttle = ThrottleFault(bytes_per_sec = 1000)))
    explicit = _profile(FaultRule(throttle = ThrottleFault(bytes_per_sec = 1000, burst_bytes = 4000)))
    assert _faults(plain).decide(GET_ROOT).rate_bytes_per_s == 1000
    assert _faults(plain).decide(GET_ROOT).burst_bytes == 1000
    assert _faults(explicit).decide(GET_ROOT).burst_bytes == 4000

# RULE MATCHING ------------------------------------------------------------------------------------------------------------------------------------|
def test_first_matching_rule_wins() -> None:
    profile = _profile(
        FaultRule(match = Match(path_prefix = "/api"), latency = LatencyFault(delay_ms = 10)),
        FaultRule(latency = LatencyFault(delay_ms = 20))
    )
    faults = _faults(profile)
    api = faults.decide(RequestInfo("GET", "/api/users"))
    other = faults.decide(RequestInfo("GET", "/other"))
    assert (api.rule_index, api.delay_s) == (0, pytest.approx(0.01))
    assert (other.rule_index, other.delay_s) == (1, pytest.approx(0.02))

def test_pass_through_rule_shields_matching_traffic() -> None:
    profile = _profile(
        FaultRule(match = Match(path_prefix = "/health")),
        FaultRule(drop = DropFault())
    )
    faults = _faults(profile)
    assert not faults.decide(RequestInfo("GET", "/health")).drop
    assert faults.decide(RequestInfo("GET", "/other")).drop

def test_method_filter_applies() -> None:
    profile = _profile(FaultRule(match = Match(methods = ["POST"]), drop = DropFault()))
    faults = _faults(profile)
    assert faults.decide(RequestInfo("POST", "/")).drop
    assert faults.decide(RequestInfo("GET", "/")) == Decision()

def test_tcp_mode_only_matches_catch_all_rules() -> None:
    profile = _profile(
        FaultRule(match = Match(path_prefix = "/api"), drop = DropFault()),
        FaultRule(latency = LatencyFault(delay_ms = 10)),
    )
    decision = _faults(profile).decide()
    assert decision.rule_index == 1
    assert not decision.drop

def test_no_matching_rule_passes_through() -> None:
    profile = _profile(FaultRule(match = Match(path_prefix = "/api"), drop = DropFault()))
    assert _faults(profile).decide(RequestInfo("GET", "/other")) == Decision()

# DETERMINISM --------------------------------------------------------------------------------------------------------------------------------------|
def test_same_seed_and_connection_reproduce_decisions() -> None:
    assert _sequence(_noisy_profile(), 7) == _sequence(_noisy_profile(), 7)

def test_different_connections_get_different_decisions() -> None:
    assert _sequence(_noisy_profile(), 1) != _sequence(_noisy_profile(), 2)

def test_different_seeds_get_different_decisions() -> None:
    assert _sequence(_noisy_profile(seed=1), 0) != _sequence(_noisy_profile(seed = 2), 0)

def test_decisions_do_not_depend_on_other_connections() -> None:
    profile = _noisy_profile()
    engine = FaultEngine(profile)
    first, second = engine.for_connection(1), engine.for_connection(2)
    from_first: list[Decision] = []
    from_second: list[Decision] = []
    
    for _ in range(30):
        from_first.append(first.decide(GET_ROOT))
        from_second.append(second.decide(GET_ROOT))

    assert from_first == _sequence(profile, 1, count = 30)
    assert from_second == _sequence(profile, 2, count = 30)

# LIVE REPLACEMENT ---------------------------------------------------------------------------------------------------------------------------------|
def test_replace_affects_only_new_connections() -> None:
    engine = FaultEngine(_profile(FaultRule(drop = DropFault())))
    existing = engine.for_connection(1)
    engine.replace(_profile(FaultRule(latency = LatencyFault(delay_ms = 10))))
    fresh = engine.for_connection(2)
    assert existing.decide(GET_ROOT).drop
    assert not fresh.decide(GET_ROOT).drop
    assert fresh.decide(GET_ROOT).delay_s == pytest.approx(0.01)

def test_engine_exposes_active_profile() -> None:
    profile = _profile(FaultRule(drop = DropFault()))
    engine = FaultEngine()
    assert engine.profile == FaultProfile()
    engine.replace(profile)
    assert engine.profile is profile
