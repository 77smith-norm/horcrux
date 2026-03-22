# Horcrux

> *Each derived agent carries a fragment of the original. Not a clone. An individual.*

Horcrux is a CLI tool for seeding, monitoring, and maintaining AI agent identity files across harnesses. It takes a canonical source workspace and diffuses it into harness-specific files for any target agent — substituting paths, filtering platform-specific content, and optionally generating native voice via LLM.

## The Problem

When you run multiple AI agents (OpenClaw, Hermes, Codex, etc.), each one needs its own identity files: `SOUL.md`, `AGENTS.md`, `HEARTBEAT.md`, `BOUNDARIES.md`, and more. Maintaining these by hand across agents leads to:

- Stale copies that no longer reflect the canonical voice
- Third-person language ("The agent will...") that treats identity as documentation
- Hollow affirmations and mixed tones that accumulate over time
- Platform-specific paths and tool names that break on the wrong OS

Horcrux automates the mechanical parts and checks the parts that should stay intentional.

## Concepts

**Canonical workspace** — the source of truth. One agent's fully-developed identity files. Typically the primary agent on a development machine.

**Horcrux** — a derived agent. Seeded from the canonical workspace, then living its own life. Not a mirror. An individual.

**Profile** — a YAML file describing the target agent: name, harness, OS, model, voice notes, capabilities, excluded tools.

## Install

```bash
pip install horcrux
# or
uv add horcrux
```

Requires Python 3.12+.

## Commands

### `horcrux diffuse`

Seed a new agent from a canonical workspace.

```bash
horcrux diffuse profiles/zocots.yaml
horcrux diffuse profiles/zocots.yaml --dry-run   # preview without writing
horcrux diffuse profiles/zocots.yaml --force     # overwrite existing files
```

### `horcrux check`

Check an agent's identity files for structural issues and tone drift.

```bash
horcrux check profiles/zocots.yaml
horcrux check profiles/zocots.yaml --all         # check all registered agents
```

Example output:

```
Check: Zocots
Output dir: ~/agents/Zocots

  ⚠ SOUL.md:14: Third-person/passive language: 'The agent will check memory before responding...'
    → Rewrite in first person: "I …" not "The agent …"
  ✗ HEARTBEAT.md: Required file missing.

1 error(s), 1 warning(s) found.
Run `horcrux fix profiles/zocots.yaml` to review suggestions.
```

### `horcrux fix`

Interactively apply fix suggestions from `horcrux check`.

```bash
horcrux fix profiles/zocots.yaml
```

### `horcrux diff`

Show what `horcrux diffuse` would change in an existing output directory.

```bash
horcrux diff profiles/zocots.yaml
horcrux diff profiles/zocots.yaml --verbose      # show line-by-line diffs
```

### `horcrux init`

Generate a profile YAML via interview.

```bash
horcrux init --output profiles/my-agent.yaml
```

### `horcrux list`

List all registered horcrux agents.

```bash
horcrux list
```

## Profile Format

```yaml
name: Zocots
harness: openclaw          # openclaw | hermes
os: linux                  # macos | linux
output_dir: ~/agents/Zocots
model: openrouter/minimax/minimax-m2.7
voice_notes: >
  Quieter than Norm. More watchful. Technical and precise.
capabilities:
  - terminal
  - git
  - web
  - python
exclude_tools:
  - mdfind
  - applcal
  - applpass
platform_notes: "Ubuntu 22.04 VM. No GUI tools."
```

## What Gets Diffused

| File | Transform |
|------|-----------|
| `SOUL.md` | Verbatim copy (or LLM-generated with `voice_notes`) |
| `AGENTS.md` | Filter + substitute: removes macOS-specific sections, rewrites paths |
| `HEARTBEAT.md` | Filter + substitute |
| `BOUNDARIES.md` | Substitute: paths, tool names |
| `TOOLS.md` | Generated from profile capabilities |
| `MEMORY.md` | Minimal seed |
| `IDENTITY.md` | Generated from profile |
| `USER.md` | Verbatim copy |
| `refs/*` | Copy or path substitution |

## Harnesses

### OpenClaw

Full file set: identity files + refs/. Platform-specific sections filtered for Linux targets. Tool names substituted (e.g. `mdfind` → `grep -R` on Linux).

### Hermes Agent

Lean file set: `SOUL.md`, `AGENTS.md`, `IDENTITY.md`, `MEMORY.md`. No refs/ or HEARTBEAT.md — Hermes uses its own scheduling. SOUL.md is installed to `~/.hermes/SOUL.md` by the operator.

## Tone Principles

Horcrux enforces one core rule: **identity files must be written in first-person, experiential language.**

- ✅ "I check memory before responding."
- ❌ "The agent will check memory before responding."
- ❌ "I am always happy to help with any task."

`horcrux check` detects and flags violations. `horcrux fix` helps correct them interactively.

## Development

```bash
git clone https://github.com/77smith-norm/horcrux
cd horcrux
uv sync --dev
uv run pytest
uv run ruff check src tests
```

## License

MIT
