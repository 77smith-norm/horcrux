# Horcrux

> *Each derived agent carries a fragment of the original. Not a clone. An individual.*

- [Getting Started](#getting-started)
- [Concepts](#concepts)
- [Install](#install)
- [Commands](#commands)
- [Safety](#safety)
- [Profile Format](#profile-format)
- [What Gets Diffused](#what-gets-diffused)
- [Harnesses](#harnesses)
- [Tone Principles](#tone-principles)
- [Development](#development)

Horcrux is a CLI tool for seeding, monitoring, and maintaining AI agent identity files across harnesses. It takes a canonical source workspace and diffuses it into harness-specific files for any target agent — substituting paths, filtering platform-specific content, and optionally generating native voice via LLM.

## The Problem

When you run multiple AI agents (OpenClaw, Hermes, Codex, etc.), each one needs its own identity files: `SOUL.md`, `AGENTS.md`, `HEARTBEAT.md`, `BOUNDARIES.md`, and more. Maintaining these by hand across agents leads to:

- Stale copies that no longer reflect the canonical voice
- Third-person language ("The agent will...") that treats identity as documentation
- Hollow affirmations and mixed tones that accumulate over time
- Platform-specific paths and tool names that break on the wrong OS

Horcrux automates the mechanical parts and checks the parts that should stay intentional.

## Getting Started

1. Install Horcrux:
```bash
pip install horcrux
# or
uv add horcrux
```
2. Identify your canonical workspace. In most setups, this is your primary OpenClaw workspace, such as `~/.openclaw/workspace`. You can set it per-profile with `source_root`, per-command with `--source`, or globally with `HORCRUX_SOURCE_DIR`.
   Use `overrides` in the profile when a specific client needs a custom `USER.md`, `SOUL.md`, or other source document without changing the canonical workspace.
3. Generate `profiles/zocots.yaml`:
```bash
horcrux init \
  --name Zocots \
  --harness openclaw \
  --os linux \
  --output-dir ~/agents/Zocots \
  --model openrouter/minimax/minimax-m2.7 \
  --voice-notes "Quieter than Norm. More watchful. Technical and precise." \
  --capabilities terminal \
  --capabilities git \
  --capabilities web \
  --platform-notes "Ubuntu 22.04 VM." \
  --output profiles/zocots.yaml
```
If you're running in a terminal, `horcrux init --output profiles/zocots.yaml` will
prompt for any missing fields. In non-interactive mode, provide all required flags.
4. Preview the managed output with `horcrux diffuse profiles/zocots.yaml --dry-run`.
5. Write the files with `horcrux diffuse profiles/zocots.yaml --force`.
6. Verify the result with `horcrux check profiles/zocots.yaml`.
```bash
horcrux diffuse profiles/zocots.yaml --dry-run
horcrux diffuse profiles/zocots.yaml --force
horcrux diffuse profiles/zocots.yaml --source ~/horcrux-starter --dry-run
horcrux check profiles/zocots.yaml
```
See [Commands](#commands) for the full command reference.

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
horcrux diffuse profiles/zocots.yaml --source ~/horcrux-starter
```

Source root precedence:
1. `--source`
2. `source_root` in the profile YAML
3. `HORCRUX_SOURCE_DIR`
4. `~/.openclaw/workspace`

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
horcrux diff profiles/zocots.yaml --source ~/horcrux-starter
```

### `horcrux init`

Generate a profile YAML from flags, or fall back to prompts for any missing
fields when running in a terminal.

```bash
horcrux init \
  --name Zocots \
  --harness openclaw \
  --os linux \
  --output-dir ~/agents/Zocots \
  --model openrouter/minimax/minimax-m2.7 \
  --voice-notes "Quieter than Norm. More watchful. Technical and precise." \
  --capabilities terminal \
  --capabilities git \
  --capabilities web \
  --platform-notes "Ubuntu 22.04 VM." \
  --output profiles/zocots.yaml

horcrux init --output profiles/zocots.yaml   # prompt for missing fields in a terminal
```

### `horcrux list`

List all registered horcrux agents.

```bash
horcrux list
```

## Safety

### Idempotency

- `horcrux diffuse` is idempotent: running it twice with the same inputs produces the same managed output.
- Without `--force`, Horcrux will not overwrite any managed file that already exists. It exits with an error instead.
- With `--force`, Horcrux overwrites only the files it manages for the selected harness. Unmanaged files outside the rendered file list are never touched.
- `--dry-run` shows what Horcrux would write and what extra files already exist in `output_dir`, without writing anything.

### File Safety

- Horcrux only writes to `output_dir` as declared in the profile.
- It never writes to system paths, never modifies the canonical workspace, and never deletes files.
- Files such as `profile.yaml`, local notes, or any file outside the managed set are untouched even with `--force`.
- If you use git for the target workspace, `git diff` is your safety net. Horcrux changes are ordinary file edits and are fully recoverable.

### Recommended Workflow For Cautious Users

1. Run `horcrux diff` first and review what would change.
2. Run `horcrux diffuse --dry-run` and confirm the output list.
3. Run `horcrux diffuse --force` to apply.

## Profile Format

```yaml
name: Zocots
harness: openclaw          # openclaw | hermes
os: linux                  # macos | linux
output_dir: ~/agents/Zocots
source_root: ~/horcrux-starter  # optional; otherwise uses HORCRUX_SOURCE_DIR or ~/.openclaw/workspace
overrides:
  USER.md: ~/clients/zocots/USER.md
  SOUL.md: ~/clients/zocots/SOUL.md
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

Override keys use the canonical document path (`USER.md`, `SOUL.md`, `refs/HANDOFF.md`, and so on). Override values point to local files that replace the canonical document during rendering.

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
| `refs/*.md` | OpenClaw only: selected files are copied or path-substituted |

Actual managed files depend on the harness. Hermes does not diffuse `refs/`.

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
