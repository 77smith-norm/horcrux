# Horcrux init — Agent-Friendly Refactor Plan

Date: 2026-03-22

## Problem

`horcrux init` is a pure interactive interview. Every field uses `typer.prompt()`.
An agent running headlessly can't use it — no TTY, no stdin, prompts either hang or crash.
The interview is fine for humans, but agents are the primary users of horcrux.

## Design

Make all profile fields passable as CLI flags. When all required fields are provided, skip
the interview entirely and write the profile immediately. When running in a TTY and fields
are missing, fall back to the existing interview flow for those fields only.

Non-interactive (agent) invocation:
```
horcrux init \
  --name Zocots \
  --harness openclaw \
  --os linux \
  --output-dir ~/agents/Zocots \
  --model openrouter/minimax/minimax-m2.7 \
  --voice-notes "Quieter than Norm. Watchful and precise." \
  --capabilities terminal --capabilities git --capabilities web \
  --platform-notes "Ubuntu 22.04 VM." \
  --output profiles/zocots.yaml
```

Interactive (human) invocation — unchanged behavior, all prompts fire for any missing field:
```
horcrux init --output profiles/new-agent.yaml
```

## Required fields (must be provided via flag or prompt)

- `--name` — agent name
- `--harness` — openclaw | hermes (default: openclaw)
- `--os` — linux | macos (default: linux)
- `--output-dir` — absolute or ~ path for the agent's output directory
- `--model` — model string (default: openrouter/minimax/minimax-m2.7)
- `--voice-notes` — character description (1–3 sentences)

## Optional fields

- `--capabilities` — repeatable flag, e.g. `--capabilities terminal --capabilities git`
- `--exclude-tools` — repeatable flag
- `--platform-notes` — free text

## Implementation

### 1. Refactor `src/horcrux/init_flow.py`

Add a new function `build_profile_yaml(...)` that takes all fields as Python arguments
and returns the YAML string. This is pure logic, no I/O, fully testable.

Keep `run_init_interview()` but refactor it to:
- Accept optional pre-filled values for each field
- Only prompt for fields that are None/empty
- Call `build_profile_yaml()` at the end

### 2. Refactor `src/horcrux/cli.py` — `init_profile` command

Add all fields as `typer.Option` parameters with `default=None`.

Logic:
```python
# All required fields present → skip interview, build directly
if all required fields provided:
    result = build_profile_yaml(name, harness, os_val, output_dir, model, voice_notes, ...)
else:
    # Fall back to interview, passing pre-filled values
    result = run_init_interview(name=name, harness=harness, ...)
```

For `--capabilities` and `--exclude-tools`, use `List[str]` with
`typer.Option(default_factory=list)`.

### 3. Non-TTY guard

If not all required fields are provided AND stdin is not a TTY
(`not sys.stdin.isatty()`), print a clear error message listing the missing
required fields and exit with code 1. Don't hang.

Error message format:
```
horcrux init: missing required fields for non-interactive mode.
Provide all required flags or run interactively in a terminal.

Missing:
  --name
  --voice-notes

Required flags: --name --harness --os --output-dir --model --voice-notes
```

### 4. Update docs

- Update `skills/horcrux/SKILL.md` — replace the init example with the flag-based form
- Update README.md `horcrux init` docs — show the flag-based invocation as primary,
  mention the interactive fallback
- Update the Getting Started section if it references `init`

### 5. Tests

Add to `tests/test_init_flow.py` (create if not exists):

- `test_build_profile_yaml_all_fields` — call with all fields, assert YAML is valid and
  contains expected values
- `test_build_profile_yaml_empty_lists` — capabilities=[], exclude_tools=[] renders cleanly
- `test_cli_init_noninteractive` — invoke CLI with all flags via CliRunner, assert profile
  written correctly, no prompts fired
- `test_cli_init_missing_required_noninteractive` — mock `sys.stdin.isatty()` to return
  False, omit --name, assert exit code 1 and helpful error message

## Quality Gates

- `uv run pytest` green
- `uv run ruff check src tests` clean
- `uv run ty check src` clean
- `horcrux init --help` shows all new flags
- Running with all flags produces valid YAML without any prompts

## Commit order

1. Refactor `init_flow.py` — extract `build_profile_yaml`, make `run_init_interview` accept pre-fills
2. Refactor CLI — add flags, non-TTY guard
3. Tests
4. Docs (SKILL.md, README)

## Compaction recovery

Re-read `docs/2026-03-22-init-agent-plan.md` and run `git log --oneline -10` before continuing.
