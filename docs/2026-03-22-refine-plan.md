# Horcrux — Refine & Refactor Plan
_2026-03-22 — Codex delegation from Norm (harness engineer)_

## Context

Horcrux Phases 1–4 are complete. 22 tests pass, ruff clean, CI on push.
This plan is a refinement pass — no new features. Improve what exists:
code quality, test coverage, edge case handling, and real-world robustness.

## Quality Gate

At every step:
```bash
uv run pytest            # must be green before commit
uv run ruff check src tests   # must be clean before push
```

TCR: write test → run pytest → GREEN: commit / RED: revert and decompose.

## Refine Areas (ordered by priority)

### 1. `horcrux diff` — improve output quality

Current: `differ.py` produces structural diffs but the output is flat. 
Improve:
- Show added/removed sections by heading, not just raw line diffs
- Colorize output using `rich` (already likely transitive via typer) or keep plain if not available
- `--verbose` flag shows full unified diff per file; default shows summary only
- Add `test_diff.py` coverage for the new summary-vs-verbose behavior

### 2. `horcrux check` — expand tone rules

Current: detects third-person patterns and a handful of hollow phrases.
Expand:
- Add detection for passive constructions: "will be done", "should be noted", "can be used"
- Add detection for hedge inflation: "basically", "essentially", "kind of", "sort of" in identity files
- Add detection for imperative-mode instructions written as second-person: "You should...", "You can..."
- Cover `HEARTBEAT.md` and `BOUNDARIES.md` in tone checks (currently only SOUL.md and AGENTS.md)
- Each new rule needs a unit test

### 3. `horcrux fix` — make it more useful

Current: interactively prompts for replacement text line by line. Very manual.
Improve:
- For tone issues with a suggestion, pre-fill the prompt with the line and suggestion so the user edits in place rather than typing from scratch (use `typer.prompt` with `default=`)
- Add a `--auto` flag that applies safe auto-fixes without confirmation (e.g. clearly hollow phrases → delete the line rather than replace)
- Safety: `--auto` must never touch lines flagged as errors, only warnings with a clear pattern

### 4. `horcrux diffuse` — dry-run output clarity

Current: dry-run prints file names but not what would change.
Improve:
- In dry-run mode, show a compact diff for each file (similar to `horcrux diff`)
- "Would write N files (M unchanged, K new)" summary line at the end

### 5. `registry.py` — robustness

Current: reads/writes `~/.horcrux/agents.json`. No handling for:
- Concurrent writes (rare but possible)
- Corrupt/partial JSON on disk
- Missing `~/.horcrux/` directory on first use

Fix:
- Create directory on first write if missing (it probably does this, verify and add test)
- Wrap JSON parse in try/except with a clear error message if corrupt
- Add a `test_registry.py` with these edge cases covered

### 6. Test coverage gaps

Run `uv run pytest --co -q` and look at what's not covered. Specifically:
- `init_flow.py` — the interview flow. Add a test using `CliRunner` with `input=` to simulate user answers
- `fix.py` — needs a test for the interactive loop using `CliRunner` with `input=`
- `source.py` — test behavior when `AGENTS.md` or other expected files are missing from the canonical workspace

### 7. Minor cleanup

- `check.py`: convert `Severity` to `StrEnum` properly (currently has `# noqa: UP042`)
- `cli.py`: `diff` command loads source but some targets don't use it — verify no redundant calls
- Ensure all public functions in `transforms/` have docstrings
- `__init__.py`: confirm `__version__` is exported and matches `pyproject.toml`

## Done When

- `uv run pytest` — green, coverage meaningfully higher than current
- `uv run ruff check src tests` — clean, no noqa suppressions left (or all are justified)
- `git log --oneline` shows atomic commits per area above
- `horcrux check`, `horcrux diff`, `horcrux fix`, `horcrux diffuse --dry-run` all work correctly on `profiles/zocots.yaml`

## Compaction Recovery

If context compacts:
1. `cat docs/2026-03-22-refine-plan.md`
2. `git log --oneline -20`
3. `uv run pytest` — confirm green
4. Find next incomplete section above, resume.
