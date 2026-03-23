"""Agent profile loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

Harness = str
TargetOS = Literal["linux", "macos"]


class AgentProfile(BaseModel):
    """Validated target agent profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    harness: Harness
    os: TargetOS
    output_dir: Path
    source_root: Path | None = None
    overrides: dict[str, Path] = Field(default_factory=dict)
    harness_plugin: Path | None = None
    model: str
    voice_notes: str
    capabilities: list[str] = Field(default_factory=list)
    exclude_tools: list[str] = Field(default_factory=list)
    platform_notes: str = ""

    @field_validator("name", "model", "voice_notes", "platform_notes", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name", "model", "voice_notes")
    @classmethod
    def _validate_required_text(cls, value: str, info: ValidationInfo) -> str:
        if not value:
            raise ValueError(f"{info.field_name} must not be empty")
        return value

    @field_validator("output_dir", "source_root", "harness_plugin", mode="before")
    @classmethod
    def _coerce_paths(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser()
        return value

    @field_validator("overrides", mode="before")
    @classmethod
    def _coerce_overrides(cls, value: object) -> object:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return value
        return {key: Path(str(path)).expanduser() for key, path in value.items()}

    @field_validator("capabilities", "exclude_tools", mode="before")
    @classmethod
    def _normalize_lists(cls, value: object) -> object:
        if value is None:
            return []
        return value

    @field_validator("capabilities", "exclude_tools")
    @classmethod
    def _dedupe_lists(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            candidate = item.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized


def load_profile(profile_path: Path | str) -> AgentProfile:
    """Load and validate an agent profile from YAML."""

    path = Path(profile_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"profile {path} is empty")
    if not isinstance(raw, dict):
        raise ValueError(f"profile {path} must contain a YAML mapping")
    return AgentProfile.model_validate(raw)
