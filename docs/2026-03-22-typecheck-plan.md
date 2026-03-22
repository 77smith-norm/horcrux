# Horcrux — Type Checking & Complexity Enforcement Plan
_2026-03-22 — Codex delegation from Norm_

## Context

`ty` (Astral's type checker) and McCabe complexity limits (C901, max 10) have been added to `pyproject.toml` and `ARCHITECTURE.md`. 

**Current violations to fix:**

### Ruff C901 (complexity > 10)
1. `src/horcrux/check.py:199` — `_check_tone` (complexity 12)
2. `src/horcrux/differ.py:175` — `_print_diff_report` (complexity 11)

### ty type errors (4 errors)
1. `src/horcrux/differ.py:19` — `Console = None` assigned to typed name. Fix: use `Console: type[Console] | None = None` or restructure with `TYPE_CHECKING` guard.
2. `src/horcrux/fix.py:102` — `report.output_dir / relative_path` — `output_dir` typed as `object`. Fix: tighten `CheckReport.output_dir` type to `Path`.
3. `src/horcrux/fix.py:108` — `_AUTO_FIX_RULES[issue.rule_id]` — `rule_id` typed as `str | None`. Fix: guard with `if issue.rule_id is None: continue` before the lookup, or tighten `CheckIssue.rule_id` to `str` where it's guaranteed present.
4. `src/horcrux/registry.py:18` — `fcntl = None` assigned to module type. Fix: same pattern as Console — use `TYPE_CHECKING` or explicit `ModuleType | None`.

---

## Quality Gate

```bash
uv run pytest            # green before every commit
uv run ruff check src tests   # must include C901 clean
uv run ty check src      # zero errors before final commit
```

TCR: fix → run all three → GREEN: commit / RED: revert. Commit after each section.

---

## Section 1 — Fix complexity violations

**`_check_tone` in `check.py` (complexity 12 → ≤ 10):**
Extract sub-checks into named helpers, e.g.:
- `_check_third_person(lines, rel_path, report)`
- `_check_hollow_affirmations(lines, rel_path, report)`
- `_check_passive_constructions(lines, rel_path, report)`
- `_check_hedge_inflation(lines, rel_path, report)`
- `_check_second_person(lines, rel_path, report)`

`_check_tone` becomes an orchestrator that calls each helper. Each helper is ≤ 10 complexity.

**`_print_diff_report` in `differ.py` (complexity 11 → ≤ 10):**
Extract the verbose unified-diff rendering into a helper: `_print_verbose_diff(printer, file_diff)`. The orchestrator calls it conditionally.

**Done when:** `uv run ruff check src tests` shows zero C901 violations. All 41+ tests still green. Commit: `refactor: decompose complex functions to meet C901 limit`.

---

## Section 2 — Fix ty type errors

Fix all 4 in order. Read `ARCHITECTURE.md` → "Type Discipline" section for the approved patterns.

**differ.py Console:**
```python
# Before:
try:
    from rich.console import Console
except ImportError:
    Console = None

# After:
try:
    from rich.console import Console as Console
except ImportError:  # pragma: no cover
    Console = None  # type: ignore[assignment]  -- acceptable platform fallback
```
Or use a proper `TYPE_CHECKING` guard if Console is only used in type annotations.
The simplest fix: add `# type: ignore[assignment]` with a comment explaining it's an intentional platform fallback.

**fix.py output_dir:**
Find `CheckReport` dataclass/model. Ensure `output_dir: Path` not `output_dir: object`. It should already be `Path` — if ty is complaining, it's likely because it's inferred as `object` from somewhere. Add explicit annotation.

**fix.py rule_id guard:**
Before `_AUTO_FIX_RULES[issue.rule_id]`, add:
```python
if issue.rule_id is None:
    continue
```

**registry.py fcntl:**
```python
# type: ignore[assignment]  -- intentional None sentinel for non-POSIX platforms
```

**Done when:** `uv run ty check src` shows zero errors. All tests still green. `uv run ruff check src tests` still clean. Commit: `fix: resolve all ty type errors — clean type check baseline`.

---

## Section 3 — Add type annotations to any unannotated public functions

Run: `uv run ty check src` after Section 2. If there are any `missing-return-type` or `missing-parameter-type` warnings on public functions, fix them.

Private helpers (`_foo`) are lower priority — annotate if easy, skip if complex.

**Done when:** `uv run ty check src` is clean. Commit only if changes were needed: `fix: add missing type annotations to public functions`.

---

## Section 4 — Verify and commit ARCHITECTURE.md

`ARCHITECTURE.md` already exists in the repo root. Read it. Verify:
- The layer model matches the actual code structure
- Any module that violates the "must NOT touch" column is noted (do not fix in this session — just note in a comment at bottom of ARCHITECTURE.md as "Known deviations to address")
- The quality gates section matches the actual `pyproject.toml` config

If everything checks out, commit as-is: `docs: add ARCHITECTURE.md — layer model and quality gates`.
If deviations found, document them and commit: `docs: ARCHITECTURE.md with known deviation notes`.

---

## Section 5 — Final verification

```bash
uv run pytest -v                    # all unit tests green
uv run pytest -m smoke -v           # smoke tests green
uv run ruff check src tests         # C901 clean, zero violations
uv run ty check src                 # zero type errors
git log --oneline -20               # confirm all commits landed
git push
```

Update `memory/TASK.md` to reflect horcrux polish complete.

---

## Compaction Recovery

If context compacts: re-read `docs/2026-03-22-typecheck-plan.md` and run `git log --oneline -20` to see which sections are done. Run `uv run ruff check src tests` and `uv run ty check src` to see current violation count. Continue from the first incomplete section.
