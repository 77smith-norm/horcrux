"""Shared target primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from horcrux.profile import AgentProfile
from horcrux.source import CanonicalWorkspace


@dataclass(frozen=True)
class DiffusedFile:
    """One rendered output file."""

    relative_path: Path
    content: str
    source_path: Path | None
    transforms: tuple[str, ...]


class BaseTarget(ABC):
    """Base contract for harness-specific diffusion targets."""

    harness_id: ClassVar[str]

    def __init__(self, profile: AgentProfile, source: CanonicalWorkspace) -> None:
        self.profile = profile
        self.source = source

    @abstractmethod
    def render(self) -> list[DiffusedFile]:
        """Render the managed files for this harness."""
