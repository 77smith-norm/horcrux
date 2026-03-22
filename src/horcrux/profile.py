"""Agent profile loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

Harness = Literal["openclaw", "hermes"]
TargetOS = Literal["linux", "macos"]


class AgentProfile(BaseModel):
    """Validated target agent profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    harness: Harness
    os: TargetOS
    output_dir: Path
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

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("name must not be empty")
        return value

    @field_validator("output_dir", mode="before")
    @classmethod
    def _coerce_output_dir(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser()
        return value

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

