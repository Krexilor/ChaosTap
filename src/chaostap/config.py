# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import tomllib
from os import PathLike
from pathlib import Path
from pydantic import ValidationError

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap.faults.models import FaultProfile

# ERRORS -------------------------------------------------------------------------------------------------------------------------------------------|
class ProfileError(Exception):
    """Raised when a fault profile cannot be read or is invalid."""

# LOADING ------------------------------------------------------------------------------------------------------------------------------------------|
def _describe(error: ValidationError) -> str:
    lines = []

    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "<root>"
        lines.append(f"  {location}: {item['msg']}")

    return "\n".join(lines)

def load_profile(path: str | PathLike[str]) -> FaultProfile:
    source = Path(path)

    try:
        raw = tomllib.loads(source.read_text(encoding = "utf-8"))

    except OSError as exc:
        raise ProfileError(f"cannot read profile '{source}': {exc.strerror or exc}") from exc

    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"invalid TOML in '{source}': {exc}") from exc

    try:
        return FaultProfile.model_validate(raw)

    except ValidationError as exc:
        raise ProfileError(f"invalid profile '{source}':\n{_describe(exc)}") from exc
