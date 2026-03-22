"""Structural and tone health checks for horcrux agent identity files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(str, Enum):  # noqa: UP042
    OK = "ok"
    WARN = "warn"
    ERROR = "error"


@dataclass
class CheckIssue:
    severity: Severity
    file: Path
    line: int | None
    message: str
    suggestion: str | None = None

    def __str__(self) -> str:
        loc = f":{self.line}" if self.line is not None else ""
        prefix = {"ok": "✓", "warn": "⚠", "error": "✗"}[self.severity.value]
        text = f"  {prefix} {self.file}{loc}: {self.message}"
        if self.suggestion:
            text += f"\n    → {self.suggestion}"
        return text


@dataclass
class CheckReport:
    agent_name: str
    output_dir: Path
    issues: list[CheckIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[CheckIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[CheckIssue]:
        return [i for i in self.issues if i.severity == Severity.WARN]

    @property
    def ok(self) -> bool:
        return not self.errors and not self.warnings

    def __str__(self) -> str:
        lines = [f"\nCheck: {self.agent_name}", f"Output dir: {self.output_dir}", ""]
        for issue in self.issues:
            lines.append(str(issue))
        if self.ok:
            lines.append("  ✓ No issues found.")
        else:
            counts = []
            if self.errors:
                counts.append(f"{len(self.errors)} error(s)")
            if self.warnings:
                counts.append(f"{len(self.warnings)} warning(s)")
            lines.append(f"\n  {', '.join(counts)} found.")
            if any(i.suggestion for i in self.issues):
                lines.append("  Run `horcrux fix <profile>` to review suggestions.")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Expected files and size bounds
# ---------------------------------------------------------------------------

_EXPECTED_FILES: list[tuple[Path, bool]] = [
    (Path("SOUL.md"), True),
    (Path("AGENTS.md"), True),
    (Path("HEARTBEAT.md"), True),
    (Path("BOUNDARIES.md"), True),
    (Path("TOOLS.md"), True),
    (Path("MEMORY.md"), True),
    (Path("IDENTITY.md"), True),
    (Path("USER.md"), True),
    (Path("refs/GUARDRAILS.md"), False),
    (Path("refs/HANDOFF.md"), False),
    (Path("refs/OPERATIONS.md"), False),
    (Path("refs/DEVELOPMENT.md"), False),
]

_TONE_CHECK_FILES = {
    "SOUL.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "BOUNDARIES.md",
}

# (min_bytes, max_bytes) — rough sanity bounds
_SIZE_BOUNDS: dict[str, tuple[int, int]] = {
    "SOUL.md": (500, 8000),
    "AGENTS.md": (300, 8000),
    "HEARTBEAT.md": (100, 4000),
    "BOUNDARIES.md": (100, 4000),
    "TOOLS.md": (100, 6000),
    "MEMORY.md": (50, 10000),
    "IDENTITY.md": (50, 4000),
    "USER.md": (100, 8000),
}

# Passive / third-person patterns that indicate the file describes the agent
# rather than being written from the agent's perspective.
_THIRD_PERSON_PATTERNS = [
    re.compile(r"\bthe agent (will|should|must|can|does|is)\b", re.IGNORECASE),
    re.compile(r"\bthe system (will|should|must|can|does|is)\b", re.IGNORECASE),
    re.compile(r"\bit (will|should|must|is able to)\b", re.IGNORECASE),
]

_HOLLOW_PATTERNS = [
    re.compile(r"I am (always )?(happy|ready|willing) to help", re.IGNORECASE),
    re.compile(r"I('d| would) be happy to", re.IGNORECASE),
    re.compile(r"great question", re.IGNORECASE),
    re.compile(r"I will always (be )?there", re.IGNORECASE),
]

_PASSIVE_PATTERNS = [
    re.compile(r"\bwill be done\b", re.IGNORECASE),
    re.compile(r"\bshould be noted\b", re.IGNORECASE),
    re.compile(r"\bcan be used\b", re.IGNORECASE),
]

_HEDGE_PATTERNS = [
    re.compile(r"\bbasically\b", re.IGNORECASE),
    re.compile(r"\bessentially\b", re.IGNORECASE),
    re.compile(r"\bkind of\b", re.IGNORECASE),
    re.compile(r"\bsort of\b", re.IGNORECASE),
]

_SECOND_PERSON_PATTERNS = [
    re.compile(r"^\s*(?:[-*]\s+)?You should\b", re.IGNORECASE),
    re.compile(r"^\s*(?:[-*]\s+)?You can\b", re.IGNORECASE),
]


def run_structural_check(output_dir: Path, agent_name: str) -> CheckReport:
    """Run fast structural checks — no LLM required."""
    report = CheckReport(agent_name=agent_name, output_dir=output_dir)

    if not output_dir.exists():
        report.issues.append(CheckIssue(
            severity=Severity.ERROR,
            file=output_dir,
            line=None,
            message="Output directory does not exist.",
        ))
        return report

    # 1. Check expected files are present
    for rel_path, required in _EXPECTED_FILES:
        full_path = output_dir / rel_path
        if not full_path.exists():
            severity = Severity.ERROR if required else Severity.WARN
            report.issues.append(CheckIssue(
                severity=severity,
                file=rel_path,
                line=None,
                message=f"{'Required' if required else 'Optional'} file missing.",
            ))
            continue

        # 2. Size bounds check
        size = full_path.stat().st_size
        bounds = _SIZE_BOUNDS.get(rel_path.name)
        if bounds:
            min_b, max_b = bounds
            if size < min_b:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=None,
                    message=f"File suspiciously small ({size} bytes, expected ≥{min_b}).",
                    suggestion="Check that diffusion produced a complete file.",
                ))
            elif size > max_b:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=None,
                    message=f"File may be bloated ({size} bytes, expected ≤{max_b}).",
                    suggestion="Review for accumulated cruft or duplicate sections.",
                ))

        # 3. Tone checks for identity-bearing files
        if rel_path.name in _TONE_CHECK_FILES:
            _check_tone(full_path, rel_path, report)

    return report


def _check_tone(full_path: Path, rel_path: Path, report: CheckReport) -> None:
    """Check for tone drift patterns in identity files."""
    lines = full_path.read_text(encoding="utf-8").splitlines()
    for lineno, line in enumerate(lines, start=1):
        for pattern in _THIRD_PERSON_PATTERNS:
            m = pattern.search(line)
            if m:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=lineno,
                    message=f"Third-person/passive language: {line.strip()!r}",
                    suggestion='Rewrite in first person: "I …" not "The agent …"',
                ))
        for pattern in _HOLLOW_PATTERNS:
            m = pattern.search(line)
            if m:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=lineno,
                    message=f"Hollow affirmation detected: {line.strip()!r}",
                    suggestion="Remove or replace with a genuine statement.",
                ))
        for pattern in _PASSIVE_PATTERNS:
            m = pattern.search(line)
            if m:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=lineno,
                    message=f"Passive construction detected: {line.strip()!r}",
                    suggestion="Rewrite in direct voice with a named actor.",
                ))
        for pattern in _HEDGE_PATTERNS:
            m = pattern.search(line)
            if m:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=lineno,
                    message=f"Hedge inflation detected: {line.strip()!r}",
                    suggestion="Delete the hedge and state the point directly.",
                ))
        for pattern in _SECOND_PERSON_PATTERNS:
            m = pattern.search(line)
            if m:
                report.issues.append(CheckIssue(
                    severity=Severity.WARN,
                    file=rel_path,
                    line=lineno,
                    message=f"Second-person instruction detected: {line.strip()!r}",
                    suggestion='Rewrite as a first-person rule or direct imperative.',
                ))
