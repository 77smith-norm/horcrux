"""Hermes Agent harness target.

Hermes doesn't auto-load refs/ or an AGENTS.md. It uses:
  - ~/.hermes/SOUL.md      — system prompt / personality
  - project-level AGENTS.md — coding context file (optional, per-project)

We generate:
  - SOUL.md        → operator installs to ~/.hermes/SOUL.md
  - AGENTS.md      → project-level context
  - IDENTITY.md    → seed file (not read by Hermes, but useful for record-keeping)
  - MEMORY.md      → seed file

HEARTBEAT.md and refs/ are skipped — Hermes uses its own schedule/config.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from horcrux.profile import AgentProfile
from horcrux.source import CanonicalWorkspace
from horcrux.targets.openclaw import DiffusedFile
from horcrux.transforms.copy import CopyTransform
from horcrux.transforms.substitute import SubstituteTransform


@dataclass(frozen=True)
class HermesTarget:
    """Render identity files for a Hermes Agent harness."""

    profile: AgentProfile
    source: CanonicalWorkspace

    def render(self) -> list[DiffusedFile]:
        return [
            self._render_soul(),
            self._render_agents(),
            self._render_identity(),
            self._render_memory(),
        ]

    # ------------------------------------------------------------------
    # Individual file renderers
    # ------------------------------------------------------------------

    def _render_soul(self) -> DiffusedFile:
        """Copy SOUL.md verbatim — LLM generation is opt-in via --llm flag."""
        return DiffusedFile(
            relative_path=Path("SOUL.md"),
            content=self.source.read_text(Path("SOUL.md")),
            source_path=Path("SOUL.md"),
            transforms=("copy",),
        )

    def _render_agents(self) -> DiffusedFile:
        lines = [
            f"# AGENTS.md — {self.profile.name}",
            "",
            "_Context file for Hermes Agent sessions._",
            "",
            "---",
            "",
            "## Identity",
            "",
            f"- **Name:** {self.profile.name}",
            f"- **Model:** `{self.profile.model}`",
            f"- **OS:** {self.profile.os}",
            f"- **Output dir:** `{self.profile.output_dir}`",
        ]
        if self.profile.platform_notes:
            lines.append(f"- **Platform:** {self.profile.platform_notes}")
        lines.extend(["", "## Voice", "", self.profile.voice_notes, ""])

        if self.profile.capabilities:
            lines.extend(["## Capabilities", ""])
            lines.extend(f"- `{c}`" for c in self.profile.capabilities)
            lines.append("")

        if self.profile.exclude_tools:
            lines.extend(["## Excluded Tools", ""])
            lines.extend(f"- `{t}`" for t in self.profile.exclude_tools)
            lines.append("")

        lines.extend([
            "## Install note",
            "",
            "Copy `SOUL.md` to `~/.hermes/SOUL.md` to activate the personality.",
            "",
        ])

        return DiffusedFile(
            relative_path=Path("AGENTS.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-hermes-agents",),
        )

    def _render_identity(self) -> DiffusedFile:
        lines = [
            "# IDENTITY.md — Who I Am",
            "",
            "_Seed file. Edit freely after diffusion._",
            "",
            f"- **Name:** {self.profile.name}",
            f"- **Harness:** {self.profile.harness}",
            f"- **OS:** {self.profile.os}",
            f"- **Model:** `{self.profile.model}`",
        ]
        if self.profile.platform_notes:
            lines.append(f"- **Platform:** {self.profile.platform_notes}")
        lines.extend(["", "## Voice", "", self.profile.voice_notes, ""])
        return DiffusedFile(
            relative_path=Path("IDENTITY.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-hermes-identity",),
        )

    def _render_memory(self) -> DiffusedFile:
        lines = [
            f"# MEMORY.md — {self.profile.name}",
            "",
            "_Seed file. Grows through use._",
            "",
            f"- Name: {self.profile.name}",
            f"- Model: `{self.profile.model}`",
            f"- Harness: {self.profile.harness}",
            "",
        ]
        return DiffusedFile(
            relative_path=Path("MEMORY.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-hermes-memory",),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _common_substitutions(self) -> tuple[tuple[str, str], ...]:
        base = Path("/home") / self.profile.name.lower() if self.profile.os == "linux" else self.profile.output_dir
        return (
            ("/Users/norm/Developer", str(base / "dev")),
            ("/Users/norm/.openclaw/workspace", str(base)),
        )
