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

Generate the profile YAML with `horcrux init`:

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

In a terminal, `horcrux init --output profiles/zocots.yaml` will prompt for any
missing fields. In non-interactive mode, provide all required flags.

Add `source_root` to the profile when the canonical workspace is not the default
`~/.openclaw/workspace` or `HORCRUX_SOURCE_DIR` location:

```yaml
source_root: ~/horcrux-starter
```

## Commands

### `horcrux diffuse`

Use `diffuse` to render the managed file set for a target harness.

```bash
horcrux diffuse profiles/zocots.yaml --dry-run
horcrux diffuse profiles/zocots.yaml --force
horcrux diffuse profiles/zocots.yaml --source ~/horcrux-starter
```

Run `--dry-run` first. Use `--force` only when you intend to overwrite existing
managed files.

Source root precedence:
1. `--source`
2. `source_root` in the profile
3. `HORCRUX_SOURCE_DIR`
4. `~/.openclaw/workspace`

### `horcrux diff`

Use `diff` when the output directory already exists and you want to review what
Horcrux would change.

```bash
horcrux diff profiles/zocots.yaml
horcrux diff profiles/zocots.yaml --verbose
horcrux diff profiles/zocots.yaml --source ~/horcrux-starter
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

1. Generate or update the profile YAML for the derived agent with `horcrux init`.
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
