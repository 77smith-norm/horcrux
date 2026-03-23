# AGENTS.md — Horcrux

## What This Is

Horcrux is a CLI tool for seeding, monitoring, and maintaining agent identity across harnesses.

An agent identity is a set of files (SOUL.md, AGENTS.md, HEARTBEAT.md, BOUNDARIES.md, etc.) that define who an agent is, how they operate, and what they value. Horcrux:
1. **diffuse** — seeds a new agent from a canonical source workspace
2. **check** — diagnoses an existing agent for drift, tone issues, passive language
3. **fix** — applies suggested corrections with approval

Each derived agent is called a **horcrux**: a fragment of the original, living its own life.

## Architecture

```
src/horcrux/
  cli.py              # typer entry point
  profile.py          # pydantic profile model + YAML loader
  source.py           # canonical workspace reader + resolve_source_root()
  transforms/
    base.py           # Transform protocol
    copy.py           # verbatim copy
    filter.py         # section filter/strip
    substitute.py     # token substitution
    llm.py            # LLM-assisted generation (Phase 2)
  targets/
    openclaw.py       # OpenClaw harness target
    hermes.py         # Hermes Agent harness target (Phase 2)
  check.py            # health checks + tone analysis (Phase 3)
  fix.py              # interactive fix application (Phase 3)
  registry.py         # ~/.horcrux/agents.json
```

## Active Plan

The active plan is `docs/2026-03-22-multi-client-plan.md`. All other plan docs are historical records.

## TCR Rules

- Red → Green → Refactor. Commit after green, before refactor.
- Every plan step has a test command before implementation starts.
- `uv run pytest` is the test command. It must pass before any commit.

## Compaction Recovery

If context compacts:
1. `cat docs/2026-03-22-horcrux-plan.md`
2. `git log --oneline -20`
3. `uv run pytest` — confirm green
4. Identify next incomplete plan step
5. Resume. Do not restart.

## Constraints

- Python 3.12+, uv, typer, pydantic, ruff
- `src/` layout — package is `src/horcrux/`
- All public functions typed
- No LLM calls in Phase 1 — that's Phase 2
- Output dir only — never install to harness config locations
- MIT license
