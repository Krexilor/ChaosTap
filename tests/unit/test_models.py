# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import pytest
from pydantic import ValidationError

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.faults.models import DropFault, ErrorFault, FaultProfile, FaultRule, LatencyFault, Match, ThrottleFault

# FAULT SPECS --------------------------------------------------------------------------------------------------------------------------------------|
@pytest.mark.parametrize("probability", [-0.1, 1.1])
def test_probability_must_be_between_zero_and_one(probability: float) -> None:
    with pytest.raises(ValidationError):
        DropFault(probability = probability)

@pytest.mark.parametrize("status", [200, 404, 499, 600])
def test_error_status_must_be_5xx(status: int) -> None:
    with pytest.raises(ValidationError):
        ErrorFault(status = status)

def test_error_defaults_to_503() -> None:
    assert ErrorFault().status == 503

@pytest.mark.parametrize("field", ["delay_ms", "jitter_ms"])
def test_latency_values_cannot_be_negative(field: str) -> None:
    with pytest.raises(ValidationError):
        LatencyFault(**{"delay_ms": 1, field: -1})

def test_throttle_rate_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ThrottleFault(bytes_per_sec = 0)

def test_throttle_burst_defaults_to_rate() -> None:
    assert ThrottleFault(bytes_per_sec = 500).effective_burst == 500
    assert ThrottleFault(bytes_per_sec = 500, burst_bytes = 2000).effective_burst == 2000

def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        LatencyFault(delay_ms = 1, delay = 2)

# MATCHING -----------------------------------------------------------------------------------------------------------------------------------------|
def test_empty_match_is_catch_all() -> None:
    match = Match()
    assert match.is_catch_all
    assert match.matches("GET", "/anything")

def test_methods_are_uppercased() -> None:
    assert Match(methods = ["get", "Post"]).methods == frozenset({"GET", "POST"})

def test_method_filter() -> None:
    match = Match(methods=["POST"])
    assert match.matches("post", "/")
    assert not match.matches("GET", "/")
    assert not match.is_catch_all

def test_path_prefix_filter() -> None:
    match = Match(path_prefix="/api")
    assert match.matches("GET", "/api/users")
    assert not match.matches("GET", "/health")

# PROFILE ------------------------------------------------------------------------------------------------------------------------------------------|
def test_profile_defaults_to_no_rules() -> None:
    profile = FaultProfile()
    assert profile.seed == 0
    assert profile.rules == ()

def test_profile_accepts_rule_lists_and_stores_a_tuple() -> None:
    profile = FaultProfile.model_validate({"rules": [{"name": "a"}, {"name": "b"}]})
    assert [rule.name for rule in profile.rules] == ["a", "b"]
    assert isinstance(profile.rules, tuple)

def test_rule_without_faults_is_valid_pass_through() -> None:
    rule = FaultRule()
    assert rule.match.is_catch_all
    assert rule.latency is None
    assert rule.drop is None
    assert rule.error is None
    assert rule.throttle is None

def test_models_are_frozen() -> None:
    profile = FaultProfile()
    with pytest.raises(ValidationError):
        profile.seed = 1
