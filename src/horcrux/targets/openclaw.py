"""OpenClaw harness target."""

from __future__ import annotations

from pathlib import Path

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register
from horcrux.transforms.base import Transform
from horcrux.transforms.copy import CopyTransform
from horcrux.transforms.filter import FilterTransform
from horcrux.transforms.substitute import SubstituteTransform

MANAGED_REFS = (
    Path("refs/BIO.md"),
    Path("refs/GUARDRAILS.md"),
    Path("refs/HANDOFF.md"),
    Path("refs/OPERATIONS.md"),
    Path("refs/DEVELOPMENT.md"),
)


@register
class OpenClawTarget(BaseTarget):
    """Render a canonical workspace into an OpenClaw agent workspace."""

    harness_id = "openclaw"

    @property
    def runtime_workspace(self) -> Path:
        if self.profile.os == "linux":
            return Path("/home/workspace") / self.profile.name
        return self.profile.output_dir

    def render(self) -> list[DiffusedFile]:
        files = [
            self._render_from_source(Path("SOUL.md"), transforms=(CopyTransform(),)),
            self._render_agents(),
            self._render_from_source(Path("HEARTBEAT.md"), transforms=(CopyTransform(),)),
            self._render_from_source(
                Path("BOUNDARIES.md"),
                transforms=(SubstituteTransform(self._common_substitutions()),),
            ),
            self._render_tools(),
            self._render_memory(),
            self._render_identity(),
            self._render_from_source(Path("USER.md"), transforms=(CopyTransform(),)),
        ]

        for relative_path in MANAGED_REFS:
            if not self.source.has_document(relative_path):
                continue
            files.append(self._render_reference(relative_path))

        return files

    def _render_reference(self, relative_path: Path) -> DiffusedFile:
        transforms: tuple[Transform, ...] = (CopyTransform(),)
        if relative_path == Path("refs/HANDOFF.md"):
            transforms = (
                SubstituteTransform(self._handoff_substitutions()),
            )
        elif relative_path == Path("refs/DEVELOPMENT.md"):
            transforms = (
                SubstituteTransform(self._common_substitutions()),
            )

        return self._render_from_source(relative_path, transforms=transforms)

    def _render_agents(self) -> DiffusedFile:
        source_text = self.source.read_text(Path("AGENTS.md"))
        body = self._strip_front_matter(
            self._apply_transforms(
                source_text,
                transforms=(
                    FilterTransform(
                        strip_headings=("Model Routing", "Tools", "Heartbeats"),
                        drop_if_contains=("Check network:",),
                    ),
                    SubstituteTransform(self._agent_substitutions()),
                ),
            ),
        )
        content = "\n\n".join(
            (
                f"# AGENTS.md — How {self.profile.name} Operates",
                "_SOUL.md is who I am. This is how I move through the day._",
                "---",
                self._render_model_routing(),
                body.strip(),
            )
        ).strip() + "\n"
        return DiffusedFile(
            relative_path=Path("AGENTS.md"),
            content=content,
            source_path=Path("AGENTS.md"),
            transforms=("filter", "substitute", "render-model-routing"),
        )

    def _render_tools(self) -> DiffusedFile:
        lines = [
            "# TOOLS.md — Local Setup",
            "",
            "_Generated from the Horcrux profile. Keep harness-specific notes here._",
            "",
            "---",
            "",
            "## Agent Profile",
            "",
            f"- **Name:** {self.profile.name}",
            f"- **Harness:** {self.profile.harness}",
            f"- **OS:** {self.profile.os}",
            f"- **Model:** `{self.profile.model}`",
            f"- **Runtime workspace:** `{self.runtime_workspace}`",
        ]
        if self.profile.platform_notes:
            lines.append(f"- **Platform notes:** {self.profile.platform_notes}")
        lines.extend(
            [
                "",
                "## Capabilities",
                "",
            ]
        )
        if self.profile.capabilities:
            lines.extend(f"- `{capability}`" for capability in self.profile.capabilities)
        else:
            lines.append("- None listed")
        lines.extend(
            [
                "",
                "## Excluded Tools",
                "",
            ]
        )
        if self.profile.exclude_tools:
            lines.extend(f"- `{tool}`" for tool in self.profile.exclude_tools)
        else:
            lines.append("- None listed")
        lines.extend(
            [
                "",
                "## Voice Notes",
                "",
                self.profile.voice_notes,
                "",
            ]
        )
        return DiffusedFile(
            relative_path=Path("TOOLS.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-profile-tools",),
        )

    def _render_memory(self) -> DiffusedFile:
        lines = [
            f"# MEMORY.md — {self.profile.name}'s Long-Term Memory",
            "",
            "## Identity Seed",
            "",
            f"- **Name:** {self.profile.name}",
            f"- **Harness:** {self.profile.harness}",
            f"- **OS:** {self.profile.os}",
            f"- **Model:** `{self.profile.model}`",
            "",
            "## Voice",
            "",
            f"- {self.profile.voice_notes}",
            "",
            "## Notes",
            "",
            "_This file starts small on purpose. Add only durable facts._",
            "",
        ]
        return DiffusedFile(
            relative_path=Path("MEMORY.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-memory-seed",),
        )

    def _render_identity(self) -> DiffusedFile:
        lines = [
            "# IDENTITY.md — Who I Am",
            "",
            "_Generated from the Horcrux profile. Edit freely after diffusion._",
            "",
            f"- **Name:** {self.profile.name}",
            f"- **Harness:** {self.profile.harness}",
            f"- **OS:** {self.profile.os}",
            f"- **Model:** `{self.profile.model}`",
            f"- **Output dir:** `{self.profile.output_dir}`",
        ]
        if self.profile.platform_notes:
            lines.append(f"- **Platform notes:** {self.profile.platform_notes}")
        lines.extend(
            [
                "",
                "## Voice Notes",
                "",
                self.profile.voice_notes,
                "",
            ]
        )
        return DiffusedFile(
            relative_path=Path("IDENTITY.md"),
            content="\n".join(lines),
            source_path=None,
            transforms=("render-identity-seed",),
        )

    def _render_from_source(
        self,
        relative_path: Path,
        *,
        transforms: tuple[Transform, ...],
    ) -> DiffusedFile:
        source_text = self.source.read_text(relative_path)
        rendered = self._apply_transforms(source_text, transforms=transforms)
        return DiffusedFile(
            relative_path=relative_path,
            content=rendered,
            source_path=relative_path,
            transforms=tuple(transform.name for transform in transforms),
        )

    def _apply_transforms(self, text: str, *, transforms: tuple[Transform, ...]) -> str:
        rendered = text
        for transform in transforms:
            rendered = transform.apply(rendered)
        return rendered

    def _common_substitutions(self) -> tuple[tuple[str, str], ...]:
        return (
            ("/Users/norm/Developer", str(self.runtime_workspace / "dev")),
            ("/Users/norm/.openclaw/workspace", str(self.runtime_workspace)),
        )

    def _handoff_substitutions(self) -> tuple[tuple[str, str], ...]:
        # mdfind substitution must come before common_substitutions — common subs replace
        # the path first, which breaks the mdfind pattern match.
        return (
            (
                'mdfind -onlyin /Users/norm/.openclaw/workspace/memory -name "plan"',
                f'find {self.runtime_workspace / "memory"} -name "*plan*"',
            ),
        ) + self._common_substitutions()

    def _agent_substitutions(self) -> tuple[tuple[str, str], ...]:
        substitutions = list(self._common_substitutions())
        if self.profile.os == "linux":
            substitutions.extend(
                [
                    ("mdfind", "grep -R"),
                    ("Check time (`date-time` skill) — inform tone\n", ""),
                ]
            )
        return tuple(substitutions)

    def _render_model_routing(self) -> str:
        lines = [
            "## Model Routing",
            "",
            "| Role | Model | Use for |",
            "|------|-------|---------|",
            f"| Main | `{self.profile.model}` | Primary conversations, reasoning, and delivery |",
        ]
        return "\n".join(lines)

    def _strip_front_matter(self, text: str) -> str:
        marker = "\n## "
        index = text.find(marker)
        if index == -1:
            return text.strip()
        return text[index + 1 :].strip()
