Implement Phase 1 of Horcrux. The active plan is docs/2026-03-22-horcrux-plan.md.

## What you're building

Horcrux is a CLI tool that takes a canonical agent identity workspace (SOUL.md, AGENTS.md, HEARTBEAT.md, BOUNDARIES.md, TOOLS.md, MEMORY.md, IDENTITY.md, USER.md, refs/) and diffuses it into a derived agent workspace using platform-specific transforms from an agent profile.

## Phase 1 steps (TCR order)

1. pyproject.toml — src/ layout, typer + pydantic + PyYAML + ruff + pytest as deps, entry point `horcrux = "horcrux.cli:app"`, Python 3.12+, MIT license
2. src/horcrux/profile.py — pydantic model + YAML loader for agent profiles
3. src/horcrux/source.py — reads canonical workspace files from a directory
4. src/horcrux/transforms/base.py — Transform protocol (typing.Protocol)
5. src/horcrux/transforms/copy.py — verbatim copy transform
6. src/horcrux/transforms/filter.py — section filter/strip transform
7. src/horcrux/transforms/substitute.py — token substitution transform
8. src/horcrux/targets/openclaw.py — maps source files to transforms for OpenClaw harness
9. src/horcrux/registry.py — read/write ~/.horcrux/agents.json
10. src/horcrux/cli.py — `horcrux diffuse <profile> [--dry-run] [--force]` and `horcrux list`
11. tests/ — fixtures + tests for transforms, profile loading, dry-run output

## Profile to create

Create `profiles/zocots.yaml`:
```yaml
name: Zocots
harness: openclaw
os: linux
output_dir: /Users/norm/.openclaw/workspace/agents/Zocots
model: openrouter/minimax/minimax-m2.7
voice_notes: "Quieter than Norm. More watchful. Technical and precise."
capabilities:
  - terminal
  - git
  - web
  - python
exclude_tools:
  - mdfind
  - applcal
  - applpass
  - remindctl
platform_notes: "Zo Computer VM — Ubuntu 22.04. No GUI tools. No macOS paths."
```

## Canonical source for testing

- Canonical workspace (diffuse FROM): `/Users/norm/.openclaw/workspace/`
- Known-good target (validate AGAINST): `/Users/norm/.openclaw/workspace/agents/Zocots/`

## Done when

`uv run pytest` passes and `uv run horcrux diffuse profiles/zocots.yaml --dry-run` runs without error and produces meaningful output.

## Constraints

- Python 3.12+, uv, typed throughout, no LLM calls in Phase 1
- `src/` layout — package at `src/horcrux/`
- MIT license
- TCR: red → green → commit → refactor. `uv run pytest` must pass before every commit.
- Commit often with meaningful messages. Push when complete.

## Compaction recovery

If context compacts:
1. `cat docs/2026-03-22-horcrux-plan.md`
2. `git log --oneline -20`
3. `uv run pytest`
4. Resume from next incomplete step. Do not restart.
