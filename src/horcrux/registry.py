"""Registry persistence."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

try:  # pragma: no cover - Windows fallback is exercised by the null branch.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

REGISTRY_ENV_VAR = "HORCRUX_REGISTRY_PATH"
DEFAULT_REGISTRY_PATH = Path.home() / ".horcrux" / "agents.json"


class RegistryError(RuntimeError):
    """Raised when the registry cannot be read or written safely."""


class RegistryEntry(BaseModel):
    """Tracked horcrux record."""

    model_config = ConfigDict(extra="forbid")

    name: str
    profile: Path
    output_dir: Path
    diffused_at: datetime
    checked_at: datetime | None = None
    soul_reviewed: bool = False


class Registry(BaseModel):
    """All tracked horcrux agents."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    agents: list[RegistryEntry] = Field(default_factory=list)


def default_registry_path() -> Path:
    """Return the default registry path, with env override support."""

    override = os.environ.get(REGISTRY_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_REGISTRY_PATH


def load_registry(path: Path | str | None = None) -> Registry:
    """Load the registry, returning an empty registry when absent."""

    registry_path = Path(path) if path is not None else default_registry_path()
    if not registry_path.exists():
        return Registry()

    with _locked_registry(registry_path):
        try:
            raw_text = registry_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Registry()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RegistryError(
            f"Registry file {registry_path} is corrupt JSON: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    try:
        return Registry.model_validate(data)
    except ValidationError as exc:
        raise RegistryError(f"Registry file {registry_path} has invalid structure.") from exc


def save_registry(registry: Registry, path: Path | str | None = None) -> Path:
    """Persist the registry to disk."""

    registry_path = Path(path) if path is not None else default_registry_path()
    payload = registry.model_dump(mode="json")

    with _locked_registry(registry_path):
        fd, temp_name = tempfile.mkstemp(
            dir=registry_path.parent,
            prefix=f".{registry_path.name}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, registry_path)
        finally:
            temp_path.unlink(missing_ok=True)

    return registry_path


def upsert_registry_entry(registry: Registry, entry: RegistryEntry) -> Registry:
    """Insert or replace a registry entry by agent name."""

    entries = [existing for existing in registry.agents if existing.name != entry.name]
    entries.append(entry)
    return Registry(version=registry.version, agents=sorted(entries, key=lambda item: item.name))


def _registry_lock_path(registry_path: Path) -> Path:
    return registry_path.with_name(f".{registry_path.name}.lock")


@contextlib.contextmanager
def _locked_registry(registry_path: Path) -> Iterator[None]:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _registry_lock_path(registry_path)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
