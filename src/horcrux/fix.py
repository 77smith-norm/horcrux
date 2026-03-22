"""Interactive fix application for horcrux check issues."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import typer

from horcrux.check import CheckIssue, CheckReport, Severity

_AUTO_FIX_RULES: dict[str, str] = {
    "hollow_affirmation": "",
}


def _split_prefix(line: str) -> tuple[str, str]:
    match = re.match(r"^(\s*(?:[-*]\s+)?)?(.*)$", line)
    if match is None:
        return "", line
    return match.group(1) or "", match.group(2)


def _draft_replacement(issue: CheckIssue, current_line: str) -> str:
    line = current_line.rstrip("\n")
    prefix, body = _split_prefix(line)

    if issue.rule_id == "third_person":
        body = re.sub(r"(?i)^the agent\s+", "I ", body)
        body = re.sub(r"(?i)^the system\s+", "I ", body)
        body = re.sub(r"(?i)^it\s+", "I ", body)
        return prefix + body

    if issue.rule_id == "hedge_inflation":
        body = re.sub(
            r"(?i)^(basically|essentially|kind of|sort of)\b[, ]*",
            "",
            body,
        )
        body = re.sub(r"\s{2,}", " ", body).strip()
        return prefix + body

    if issue.rule_id == "second_person_instruction":
        body = re.sub(r"(?i)^you should\s+", "I ", body)
        body = re.sub(r"(?i)^you can\s+", "I can ", body)
        return prefix + body

    if issue.rule_id == "hollow_affirmation":
        return ""

    return line


def _prompt_default(current_line: str) -> str:
    return current_line.rstrip("\n")


def _apply_line_change(lines: list[str], line_idx: int, replacement: str) -> tuple[bool, int]:
    if replacement == "":
        if line_idx >= len(lines):
            return False, 0
        lines.pop(line_idx)
        return True, -1

    new_line = replacement if replacement.endswith("\n") else replacement + "\n"
    if line_idx >= len(lines) or lines[line_idx] == new_line:
        return False, 0
    lines[line_idx] = new_line
    return True, 0


def _auto_fix_issues(report: CheckReport) -> list[CheckIssue]:
    blocked_lines = {
        (issue.file, issue.line)
        for issue in report.issues
        if issue.severity == Severity.ERROR and issue.line is not None
    }
    selected: list[CheckIssue] = []
    seen_lines: set[tuple[Path, int | None]] = set()

    for issue in report.issues:
        line_key = (issue.file, issue.line)
        if issue.severity != Severity.WARN:
            continue
        if issue.line is None or issue.rule_id not in _AUTO_FIX_RULES:
            continue
        if line_key in blocked_lines or line_key in seen_lines:
            continue
        selected.append(issue)
        seen_lines.add(line_key)

    return selected


def _apply_auto_fixes(report: CheckReport) -> int:
    issues_by_file: dict[Path, list[CheckIssue]] = defaultdict(list)
    for issue in _auto_fix_issues(report):
        issues_by_file[issue.file].append(issue)

    applied = 0
    for relative_path, issues in issues_by_file.items():
        full_path = report.output_dir / relative_path
        lines = full_path.read_text(encoding="utf-8").splitlines(keepends=True)
        file_changed = False

        for issue in sorted(issues, key=lambda item: item.line or 0, reverse=True):
            line_idx = (issue.line or 1) - 1
            if issue.rule_id is None:
                continue
            replacement = _AUTO_FIX_RULES[issue.rule_id]
            changed, _ = _apply_line_change(lines, line_idx, replacement)
            if changed:
                applied += 1
                file_changed = True

        if file_changed:
            full_path.write_text("".join(lines), encoding="utf-8")

    return applied


def run_fix(report: CheckReport, *, auto: bool = False) -> int:
    """Walk through fixable issues interactively. Returns count of applied fixes."""
    if auto:
        count = _apply_auto_fixes(report)
        if count == 0:
            typer.echo("No safe auto-fixes found.")
        return count

    fixable = [i for i in report.issues if i.suggestion and i.line is not None]

    if not fixable:
        typer.echo("No fixable issues found.")
        return 0

    applied = 0
    line_offsets: dict[Path, int] = defaultdict(int)
    for issue in fixable:
        typer.echo(f"\n{issue}")
        if not typer.confirm("  Apply this suggestion?", default=False):
            continue

        full_path = report.output_dir / issue.file
        lines = full_path.read_text(encoding="utf-8").splitlines(keepends=True)
        line_idx = (issue.line or 1) - 1 + line_offsets[issue.file]

        typer.echo(f"\n  Current line {issue.line}:")
        typer.echo(f"    {lines[line_idx].rstrip()}")
        typer.echo(f"  Suggestion: {issue.suggestion}")
        draft = _draft_replacement(issue, lines[line_idx])
        if draft and draft != lines[line_idx].rstrip("\n"):
            typer.echo(f"  Suggested edit: {draft}")
        elif draft == "":
            typer.echo("  Suggested edit: [delete line]")
        new_text = typer.prompt(
            "  Replacement text",
            default=_prompt_default(lines[line_idx]),
        )

        changed, delta = _apply_line_change(lines, line_idx, new_text)
        if not changed:
            typer.echo("  No change.")
            continue

        full_path.write_text("".join(lines), encoding="utf-8")
        typer.echo("  ✓ Applied.")
        applied += 1
        line_offsets[issue.file] += delta

    return applied
