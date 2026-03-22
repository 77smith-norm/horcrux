# Horcrux Polish Plan 2 — Skill, Safety Story, Docs

Date: 2026-03-22
Status: Ready for Codex

## Goals

Four concrete deliverables:

1. **AgentSkill file** (`skills/horcrux/SKILL.md`) — a drop-in skill any OpenClaw agent can copy
2. **README safety section** — explicit idempotency + safety guarantees for anxious users
3. **README getting-started walkthrough** — concrete steps from clone to first `diffuse`
4. **README minor fixes** — table of contents, correct "extra files" behavior description

No behavior changes. No new commands. Docs and skill only.

---

## Deliverable 1 — skills/horcrux/SKILL.md

Create `skills/horcrux/SKILL.md` at the repo root. This is an OpenClaw AgentSkill.

The skill should follow the AgentSkill format exactly:
- Frontmatter: `name`, `description`
- The description must be useful for skill selection — one sentence, action-oriented
- Body: what the skill does, when to use it, commands, examples

Content to cover:
- What horcrux is (one paragraph max)
- Install: `pip install horcrux` or `uv add horcrux`
- Primary workflow: `diffuse`, `check`, `diff`, `fix`
- Profile YAML format (compact — just the required fields, one example)
- When to run each command
- Important: `--dry-run` always safe, `--force` required to overwrite managed files, unmanaged files (profile.yaml, BOUNDARIES.md, etc.) are never touched

Tone: agent-facing, imperative, concise. This is a runbook, not a narrative.

Example skeleton:

```markdown
---
name: horcrux
description: >
  Seed, monitor, and maintain AI agent identity files across harnesses.
  Use when creating a new derived agent, checking an existing agent for tone
  drift or missing files, or syncing identity files after a canonical workspace
  change.
---

# Horcrux — Agent Identity Management

[body...]
```

---

## Deliverable 2 — README safety section

Add a `## Safety` section to README.md. Place it after `## Commands` and before `## Profile Format`.

Content:

**Idempotency**
- `horcrux diffuse` is idempotent: running it twice produces the same output
- Without `--force`, it will not overwrite any file that already exists — it exits with an error instead
- With `--force`, it overwrites only the files it manages (the ones in the diffuse output). Unmanaged files — anything not in the rendered file list — are never touched
- `--dry-run` shows exactly what would change without writing anything

**File safety**
- Horcrux only writes to `output_dir` as declared in the profile
- It never writes to system paths, never modifies the canonical workspace, never deletes files
- Files like `profile.yaml`, `BOUNDARIES.md`, or any file not in the managed set are untouched even with `--force`
- If you use git for your workspace (recommended), `git diff` is your safety net — horcrux changes are ordinary file edits, fully recoverable

**Recommended workflow for cautious users**
1. Run `horcrux diff` first — review what would change
2. Run `horcrux diffuse --dry-run` — confirm the output list
3. Run `horcrux diffuse --force` — apply

---

## Deliverable 3 — README getting-started walkthrough

Add a `## Getting Started` section near the top of README.md (after the intro, before `## Concepts`).

Walk through:
1. Install horcrux
2. Identify your canonical workspace (typically your primary OpenClaw agent's workspace directory)
3. Create a profile YAML for the derived agent
4. Run `horcrux diffuse profiles/my-agent.yaml --dry-run` to preview
5. Run `horcrux diffuse profiles/my-agent.yaml --force` to write
6. Run `horcrux check profiles/my-agent.yaml` to verify

Keep it under 30 lines. Use a concrete example profile (Zocots-style). Don't explain every flag — link to the Commands section.

---

## Deliverable 4 — README table of contents and minor fixes

Add a TOC to README.md at the top (after the tagline quote). Use plain markdown links. Sections to include:
- Getting Started
- Concepts
- Install
- Commands
- Safety
- Profile Format
- What Gets Diffused
- Harnesses
- Tone Principles
- Development

Also fix: the "What Gets Diffused" section currently says `refs/*` are "Copy or path substitution" — tighten this. The hermes harness doesn't copy refs/. Add a note that the actual set depends on the harness.

---

## Quality Gates

- `uv run pytest` — green (no behavior changes, just docs + new file)
- `uv run ruff check src tests` — clean
- `skills/horcrux/SKILL.md` exists and is valid markdown with frontmatter
- README.md has the Safety section, Getting Started section, and TOC

## Compaction recovery

Re-read `docs/2026-03-22-polish-2-plan.md` and `git log --oneline -10` to assess state before continuing.
