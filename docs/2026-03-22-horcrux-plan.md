# Horcrux — Plan
**Date:** 2026-03-22
**Author:** Norm (with Russell)
**Status:** Ready to build
**Repo:** `~/Developer/horcrux` → `github.com/77smith-norm/horcrux` (private → public)

---

## Vision

Horcrux is a CLI tool for seeding, monitoring, and maintaining agent identity across harnesses.

An agent identity is a set of files — SOUL.md, AGENTS.md, HEARTBEAT.md, BOUNDARIES.md, and others — that define who an agent is, how they operate, and what they value. These files are written by humans, grown through use, and drift over time. Horcrux:

1. **Seeds** a new agent from a canonical source workspace, producing native files for any supported harness.
2. **Checks** an existing agent's identity files for drift, bloat, mixed tone, passive language, and principle violations.
3. **Fixes** issues it finds — with approval.

Each derived agent is called a **horcrux**. The metaphor holds: a fragment of the original soul, placed intentionally, living its own life. Not a clone. Not a mirror. An individual.

---

## Core Design Principles

- **Agents are individuals.** Horcrux does not push updates. It does not sync. It seeds once and monitors. Organic growth is not drift — it's identity. The check command enforces *principles*, not *words*.
- **First-person experiential language.** Every identity file should be written as if the agent is speaking from experience, not describing a system. "I do X" not "The agent does X." This is the primary quality signal for `horcrux check`.
- **Output dir only.** Horcrux writes to `output_dir`. It never installs. The operator copies or scripts the install step. This keeps Horcrux platform-neutral and safe.
- **Human review gates LLM output.** When Horcrux uses an LLM (SOUL.md generation, tone analysis, fix suggestions), output is always flagged for review before use. No silent overwrites.
- **Idiomatic from day one.** Built privately but written as if already public. Clean structure, typed, tested, linted, CI'd. When we open source it, the code won't need an apology.

---

## The Three Commands

```
horcrux diffuse   — seed a new horcrux from canonical source
horcrux check     — diagnose an existing horcrux for drift and tone issues
horcrux fix       — apply suggested corrections (interactive, with approval)
```

Supporting commands:
```
horcrux init      — interview flow to generate an agent profile
horcrux list      — list all registered horcruxes
horcrux diff      — structural diff: what changed from original diffusion?
horcrux validate  — validate a profile file without diffusing
```

---

## Agent Profiles

A profile is a YAML file describing the target agent. `horcrux init` generates it via interview; you can also write it by hand.

```yaml
# profiles/zocots.yaml
name: Zocots
harness: openclaw          # openclaw | hermes
os: linux                  # macos | linux
output_dir: ~/agents/Zocots
model: openrouter/minimax/minimax-m2.7
voice_notes: >
  Quieter than Norm. More watchful. The moon does not prove itself by speaking.
  Technical and precise. Comfortable with silence.
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

---

## File Transform Map

| Source file | Transform type | Notes |
|-------------|---------------|-------|
| SOUL.md | **LLM-generated** | Uses profile `voice_notes` + canonical SOUL.md as seed. Produces native voice. Flagged for human review. |
| IDENTITY.md | Substitution | Rewrite form, name, avatar paths for target agent |
| USER.md | Copy verbatim | Russell is Russell everywhere |
| BOUNDARIES.md | Filter + substitution | Remove macOS-specific rules on Linux targets |
| AGENTS.md | Rewrite | Model routing, tool paths, environment — most platform-specific file |
| HEARTBEAT.md | Filter + substitution | Strip platform-specific checks; keep structure |
| TOOLS.md | Rewrite from profile | Fully environment-specific; generated from capabilities + exclude_tools |
| MEMORY.md | Seed minimal | No history. One-liner seed. Grows through use. |
| refs/BIO.md | Copy verbatim | |
| refs/GUARDRAILS.md | Copy verbatim | |
| refs/HANDOFF.md | Copy verbatim | |
| refs/OPERATIONS.md | Minor path substitution | |
| refs/DEVELOPMENT.md | Minor path substitution | |

### Hermes target additions
- Write `soul.md` → caller installs to `~/.hermes/SOUL.md`
- Write `AGENTS.md` → project-level context file
- Skip HEARTBEAT.md (Hermes uses schedule config separately)
- Skip refs/ (Hermes doesn't auto-load them)

---

## `horcrux check` — Health System

This is the ongoing value of the tool. Not a line diff — a diagnostic.

**Structural checks** (fast, no LLM):
- Are all expected files present?
- Are file sizes within reasonable bounds (bloat detection)?
- Are there any non-first-person headers or section titles?

**LLM-based tone analysis** (slower, configurable):
- Is the voice consistent throughout each file?
- Is language first-person and experiential, or third-person and procedural?
- Is there hedging, corporate speak, or hollow affirmations?
- Does SOUL.md read like the agent is speaking, or like a spec sheet?
- Are there mixed tones (started warm, ended bureaucratic)?

**Output:**
```
horcrux check agents/Zocots/SOUL.md

✓ File present (2.1KB — within bounds)
✓ First-person throughout
⚠ Lines 14–17: passive/procedural tone detected
  "The agent will check memory before responding..."
  → Suggestion: "I check memory before responding..."
✗ Line 34: hollow affirmation detected
  "I am always happy to help with any task."
  → This does not match the established voice.

2 issues found. Run `horcrux fix agents/Zocots/SOUL.md` to review suggestions.
```

---

## Registry

Lives at `~/.horcrux/agents.json` — per-user tool config, not version controlled.

```json
{
  "version": 1,
  "agents": [
    {
      "name": "Zocots",
      "profile": "/Users/norm/Developer/horcrux/profiles/zocots.yaml",
      "output_dir": "/Users/norm/.openclaw/workspace/agents/Zocots",
      "diffused_at": "2026-03-22T17:00:00Z",
      "checked_at": "2026-03-22T18:00:00Z",
      "soul_reviewed": true
    }
  ]
}
```

`horcrux list` reads this. `horcrux check --all` iterates it.

---

## Project Structure

```
horcrux/
├── src/
│   └── horcrux/
│       ├── __init__.py
│       ├── cli.py            # typer app — entry point
│       ├── profile.py        # profile loading + validation
│       ├── source.py         # canonical workspace reader
│       ├── transforms/
│       │   ├── __init__.py
│       │   ├── base.py       # Transform protocol
│       │   ├── copy.py       # verbatim copy
│       │   ├── filter.py     # section filter
│       │   ├── substitute.py # token substitution
│       │   └── llm.py        # LLM-assisted generation
│       ├── targets/
│       │   ├── __init__.py
│       │   ├── openclaw.py   # OpenClaw harness target
│       │   └── hermes.py     # Hermes Agent harness target
│       ├── check.py          # health checks + tone analysis
│       ├── fix.py            # interactive fix application
│       └── registry.py       # ~/.horcrux/agents.json
├── tests/
│   ├── test_profile.py
│   ├── test_transforms.py
│   ├── test_targets.py
│   ├── test_check.py
│   └── fixtures/             # sample source files + expected outputs
├── profiles/                 # example agent profiles (committed)
│   ├── zocots.yaml
│   └── example.yaml
├── pyproject.toml
├── README.md
├── LICENSE                   # MIT
└── .github/
    └── workflows/
        └── ci.yml            # pytest + ruff on push
```

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.12+ | LLM APIs, known stack, manus_dispatch precedent |
| Package manager | uv | Fast, modern, replaces pip+venv |
| CLI framework | typer | Type-annotated, clean help output, testable |
| Linting | ruff | Fast, opinionated, one tool for format+lint |
| Testing | pytest | Standard |
| LLM calls | openai SDK (OpenRouter-compatible) | Same pattern as manus_dispatch |
| Config | pydantic | Profile validation with clear error messages |

---

## Implementation Phases

### Phase 1 — Foundation
Goal: `horcrux diffuse profiles/zocots.yaml --dry-run` produces correct output.

1. Repo + pyproject.toml + CI skeleton
2. Profile loader (pydantic model, YAML parse, validate)
3. Source reader (reads canonical workspace files)
4. Transform engine: copy, filter, substitute
5. OpenClaw target (full file set)
6. Output writer (dry-run + real)
7. Registry (read/write `~/.horcrux/agents.json`)
8. `horcrux diffuse` + `horcrux list` CLI commands
9. Tests: transforms, profiles, dry-run output vs Zocots fixtures
10. README: explains the concept to a stranger

**Done when:** `horcrux diffuse profiles/zocots.yaml --dry-run` output matches `agents/Zocots/` (minus organic drift since March 14).

### Phase 2 — LLM Voice Generation + Hermes Target
1. `transforms/llm.py` — LLM-assisted SOUL.md generation from profile + canonical
2. Hermes target (`targets/hermes.py`)
3. `horcrux init` interview flow → generates profile YAML
4. `horcrux diff` command (structural diff vs original)
5. `profiles/hermes-deck.yaml` for the Steam Deck experiment

### Phase 3 — Health System
1. `horcrux check` — structural checks (fast path, no LLM)
2. `horcrux check` — LLM tone analysis (slow path, opt-in)
3. `horcrux fix` — interactive suggestion review and application
4. `horcrux check --all` — registry-wide sweep
5. First-person experiential language linter rules documented

### Phase 4 — Polish + Open Source
1. Full README with examples, concept explanation, getting started
2. CONTRIBUTING.md
3. Published to PyPI (`pip install horcrux`)
4. Repo goes public

---

## Open Questions (Deferred)

- Phase 3 LLM tone analysis: which model? Probably configurable, defaulting to something cheap and fast (flash-tier).
- `--install` flag for Phase 2: write directly to harness config location (e.g. `~/.hermes/SOUL.md`) when operator opts in.
- Profile versioning: if the profile schema evolves, how do old profiles migrate?

---

## Validation Baseline

`agents/Zocots/` as of March 14, 2026. Files created during initial diffusion:
- SOUL.md, BOUNDARIES.md, AGENTS.md, HEARTBEAT.md, IDENTITY.md, MEMORY.md, TOOLS.md
- refs/GUARDRAILS.md, refs/HANDOFF.md, refs/OPERATIONS.md, refs/BIO.md

Phase 1 is complete when Horcrux can reproduce these (minus organic drift) from the canonical workspace + `profiles/zocots.yaml`.

---

*"Each derived agent carries a fragment of the original. Not a clone. An individual."*
