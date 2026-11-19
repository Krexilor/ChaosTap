# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import pytest
from pathlib import Path

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.config import ProfileError, load_profile

# FIXTURES -----------------------------------------------------------------------------------------------------------------------------------------|
EXAMPLE_PROFILE = Path(__file__).resolve().parents[2] / "examples" / "profiles" / "flaky.toml"

VALID_TOML = """\
seed = 7

[[rules]]
name = "api"

[rules.match]
methods = ["get"]
path_prefix = "/api"

[rules.latency]
delay_ms = 50
jitter_ms = 25

[rules.error]
status = 500
probability = 0.2
"""

def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "profile.toml"
    path.write_text(text, encoding = "utf-8")
    return path

# LOADING ------------------------------------------------------------------------------------------------------------------------------------------|
def test_loads_a_valid_profile(tmp_path: Path) -> None:
    profile = load_profile(_write(tmp_path, VALID_TOML))
    rule = profile.rules[0]
    assert profile.seed == 7
    assert rule.name == "api"
    assert rule.match.methods == frozenset({"GET"})
    assert rule.match.path_prefix == "/api"
    assert rule.latency is not None
    assert rule.latency.delay_ms == 50
    assert rule.error is not None
    assert rule.error.status == 500

def test_accepts_string_paths(tmp_path: Path) -> None:
    assert load_profile(str(_write(tmp_path, "seed = 3"))).seed == 3

def test_example_profile_is_valid() -> None:
    profile = load_profile(EXAMPLE_PROFILE)
    assert profile.seed == 42
    assert len(profile.rules) == 1

# ERRORS -------------------------------------------------------------------------------------------------------------------------------------------|
def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match = "cannot read profile"):
        load_profile(tmp_path / "missing.toml")

def test_invalid_toml_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match = "invalid TOML"):
        load_profile(_write(tmp_path, "seed = = 1"))

def test_validation_errors_name_the_offending_field(tmp_path: Path) -> None:
    text = "[[rules]]\n[rules.error]\nstatus = 200\n"
    with pytest.raises(ProfileError, match = r"rules\.0\.error\.status"):
        load_profile(_write(tmp_path, text))

def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match = "invalid profile"):
        load_profile(_write(tmp_path, "sed = 1"))
