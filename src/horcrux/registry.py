"""Registry persistence."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


REGISTRY_ENV_VAR = "HORCRUX_REGISTRY_PATH"
DEFAULT_REGISTRY_PATH = Path.home() / ".horcrux" / "agents.json"


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
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return Registry.model_validate(data)


def save_registry(registry: Registry, path: Path | str | None = None) -> Path:
    """Persist the registry to disk."""

    registry_path = Path(path) if path is not None else default_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = registry.model_dump(mode="json")
    registry_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return registry_path


def upsert_registry_entry(registry: Registry, entry: RegistryEntry) -> Registry:
    """Insert or replace a registry entry by agent name."""

    entries = [existing for existing in registry.agents if existing.name != entry.name]
    entries.append(entry)
    return Registry(version=registry.version, agents=sorted(entries, key=lambda item: item.name))

