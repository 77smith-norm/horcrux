---
name: horcrux
description: >
  Seed, inspect, and update agent identity files with Horcrux when creating a
  derived agent, previewing harness-specific changes, checking for drift, or
  applying safe fixes.
---

# Horcrux

Use Horcrux to diffuse a canonical agent workspace into harness-specific identity
files and keep those files aligned over time.

## Use It When

- Create a new derived agent from a canonical workspace.
- Preview managed-file changes before writing them.
- Check an existing agent for missing files or tone drift.
- Apply safe rewrites after `horcrux check`.

## Install

```bash
pip install horcrux
# or
uv add horcrux
```

## Profile

Required fields:

```yaml
name: Zocots
harness: openclaw
os: linux
output_dir: ~/agents/Zocots
model: openrouter/minimax/minimax-m2.7
voice_notes: >
  Quieter than Norm. More watchful. Technical and precise.
```

Add `capabilities`, `exclude_tools`, and `platform_notes` when the target agent
needs them.

## Commands

### `horcrux diffuse`

Use `diffuse` to render the managed file set for a target harness.

```bash
horcrux diffuse profiles/zocots.yaml --dry-run
horcrux diffuse profiles/zocots.yaml --force
```

Run `--dry-run` first. Use `--force` only when you intend to overwrite existing
managed files.

### `horcrux diff`

Use `diff` when the output directory already exists and you want to review what
Horcrux would change.

```bash
horcrux diff profiles/zocots.yaml
horcrux diff profiles/zocots.yaml --verbose
```

### `horcrux check`

Use `check` after diffusion or after manual edits to detect missing files,
third-person language, passive voice, and similar drift.

```bash
horcrux check profiles/zocots.yaml
```

### `horcrux fix`

Use `fix` after `check` when you want to review and apply suggested rewrites.

```bash
horcrux fix profiles/zocots.yaml
```

## Primary Workflow

1. Create or update the profile YAML for the derived agent.
2. Run `horcrux diffuse <profile> --dry-run` to preview the managed file set.
3. Run `horcrux diffuse <profile> --force` to write the managed files.
4. Run `horcrux check <profile>` to verify structure and tone.
5. Run `horcrux diff <profile>` before later re-syncs.
6. Run `horcrux fix <profile>` if `check` reports issues you want to apply.

## Safety

- `horcrux diffuse --dry-run` is always non-writing.
- `horcrux diffuse` is idempotent: the same inputs render the same managed file set.
- Without `--force`, Horcrux stops if a managed destination file already exists.
- With `--force`, Horcrux overwrites only managed output files.
- Unmanaged files such as `profile.yaml` or custom notes outside the rendered file list are not touched.
- The managed file set depends on the harness. OpenClaw includes `refs/`; Hermes does not.
- Horcrux only writes inside `output_dir`. It does not modify the canonical workspace or delete files.
