# Horcrux — Polish, Smoke Test & Harness Extensibility Plan
_2026-03-22 — Codex delegation from Norm_

## Context

Horcrux refine pass (sections 1–7) is complete. 41 tests, 92% coverage, ruff clean.

This plan does three things:
1. Close the remaining coverage gaps and add a real smoke test
2. Make the harness layer properly extensible (new harness = one file + profile entry, no core changes)
3. Document the harness contract so any new harness (Codex native, OpenCode, etc.) can be added next week without touching existing code

---

## Quality Gate (same as always)

```bash
uv run pytest            # green before every commit
uv run ruff check src tests   # clean before push
```

TCR: write test → run → GREEN: commit / RED: revert. Commit after each section.

---

## Section 1 — Close coverage gaps in `fix.py` and `cli.py`

**Current:** `fix.py` at 86%, `cli.py` at 83%. Missing: deep interactive loop branches in fix, and a few CLI error paths.

**Do:**
- Add `CliRunner` tests for `fix.py` lines 35–51 (the live-prompt interaction). Use `input=` to drive the interactive flow through all branches: accept suggestion, type custom replacement, skip.
- Add `CliRunner` tests for `cli.py` lines 136–143 — the fix command edge paths (no issues found, empty agent dir).
- Target: `fix.py` ≥ 94%, `cli.py` ≥ 93%.

**Done when:** `pytest --cov` shows both files at or above target thresholds. Green + ruff clean. Commit: `test: close fix.py and cli.py coverage gaps`.

---

## Section 2 — Smoke test against real Zocots workspace

**Do:**
Add `tests/test_smoke.py` — integration tests that run against the real Zocots workspace at `/Users/norm/.openclaw/workspace/agents/Zocots`. These should be marked `@pytest.mark.smoke` and skipped in CI (add `smoke` to `markers` in `pyproject.toml`, and `--ignore` or `-m "not smoke"` as the default `addopts`).

Tests to include:
```python
# 1. horcrux check Zocots → exits zero, no errors
# 2. horcrux diff Zocots → runs without exception (may or may not find changes)
# 3. horcrux diffuse --dry-run using Zocots profile → renders all expected files, no write
```

The Zocots profile path is: `/Users/norm/.openclaw/workspace/agents/Zocots/profile.yaml`
(If it doesn't exist, the test should skip with `pytest.skip("Zocots profile not found")`)

**Done when:** `uv run pytest -m smoke` passes on this machine. `uv run pytest` (no `-m smoke`) still passes without touching real filesystem. Commit: `test: smoke tests against real Zocots workspace`.

---

## Section 3 — Harness extensibility: target registry + abstract base

**Current problem:** `Harness = Literal["openclaw", "hermes"]` in `profile.py` is a closed enum. Adding a new harness (e.g. `codex`, `opencode`, `gemini-cli`) requires editing the Literal, adding a target file, and wiring it into `cli.py` manually. No contract is enforced.

**Do:**

### 3a. Abstract base class
Create `src/horcrux/targets/base.py`:
```python
from abc import ABC, abstractmethod
from horcrux.profile import AgentProfile
from horcrux.source import CanonicalWorkspace

class BaseTarget(ABC):
    def __init__(self, profile: AgentProfile, source: CanonicalWorkspace): ...

    @abstractmethod
    def render(self) -> list[DiffusedFile]: ...

    @property
    @abstractmethod
    def harness_id(self) -> str:
        """Lowercase string matching the profile `harness` field."""
        ...
```

### 3b. Target registry
Create `src/horcrux/targets/registry.py`:
```python
_REGISTRY: dict[str, type[BaseTarget]] = {}

def register(cls: type[BaseTarget]) -> type[BaseTarget]:
    _REGISTRY[cls.harness_id] = cls  # type: ignore[attr-defined]
    return cls

def get_target(harness: str) -> type[BaseTarget]:
    if harness not in _REGISTRY:
        raise ValueError(f"Unknown harness: {harness!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[harness]
```

### 3c. Register existing targets
Add `@register` decorator to `OpenClawTarget` and `HermesTarget`. Update `__init__.py` to import both so they self-register on package load.

### 3d. Relax the Literal
Change `Harness = Literal["openclaw", "hermes"]` to `Harness = str` in `profile.py`. Validation now comes from the registry at runtime (when `get_target(profile.harness)` is called), not from Pydantic.

### 3e. Wire into CLI
In `cli.py`, replace the `if harness == "openclaw" / elif harness == "hermes"` branching with:
```python
target_cls = get_target(profile.harness)
target = target_cls(profile=profile, source=source)
files = target.render()
```

### 3f. Tests
- `test_target_registry.py`: register a mock target, look it up, confirm unknown harness raises.
- Existing hermes/openclaw tests must still pass unchanged.

**Done when:** Adding a new harness requires only: (1) create `src/horcrux/targets/myharness.py` with `@register` class, (2) import it in `targets/__init__.py`. Zero changes to `profile.py` or `cli.py`. All tests green. Commit: `feat: harness target registry — extensible without core changes`.

---

## Section 4 — Document the harness contract

Create `docs/adding-a-harness.md`:

```markdown
# Adding a New Harness to Horcrux

## What a harness target does
...

## Steps
1. Create `src/horcrux/targets/<name>.py`
2. Subclass `BaseTarget`, implement `render()` and `harness_id`
3. Decorate with `@register`
4. Add import to `src/horcrux/targets/__init__.py`
5. Add a profile YAML with `harness: <name>`
6. Add tests in `tests/test_<name>_target.py`

## Profile YAML example
...

## What render() must return
...
```

No code changes. Just the doc. Commit: `docs: harness contract — how to add a new target`.

---

## Section 5 — Final verification

```bash
uv run pytest -v                    # all unit tests green
uv run pytest -m smoke -v           # smoke tests green on this machine
uv run ruff check src tests         # clean
git log --oneline -15               # confirm all commits landed
```

Push. Update TASK.md.

---

## Compaction Recovery

If context compacts: re-read this file (`docs/2026-03-22-polish-plan.md`) and run `git log --oneline -15` to see which sections are done. Continue from the first incomplete section. Complete all five sections fully.
