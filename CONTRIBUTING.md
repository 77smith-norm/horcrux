# Contributing to Horcrux

Horcrux is a small, opinionated tool. Contributions are welcome, but the design principles are not negotiable.

## Design Principles

1. **Agents are individuals.** Horcrux seeds once and monitors. It does not push updates or sync. Organic growth in derived agents is not drift — it's identity.
2. **First-person language is the primary quality signal.** Every check and fix enforces this. Don't weaken it.
3. **Output dir only.** Horcrux writes to `output_dir`. It never installs to system locations unless the operator opts in explicitly.
4. **Human review gates LLM output.** No silent overwrites from LLM-generated content.

## Setup

```bash
uv sync --dev
uv run pytest           # must be green
uv run ruff check src tests   # must be clean
```

## Workflow

- TCR: red → green → commit → refactor.
- One commit per logical change.
- Every new behavior needs a test.
- `uv run pytest` must pass before every commit.
- `uv run ruff check src tests` must be clean before push.

## Adding a Harness Target

1. Create `src/horcrux/targets/<harness>.py`
2. Implement a class with a `render() -> list[DiffusedFile]` method
3. Add the harness name to `Harness` in `profile.py`
4. Wire it into `_build_target()` in `cli.py`
5. Add tests in `tests/test_<harness>_target.py`
6. Document the file set in README.md

## Adding a Transform

1. Create `src/horcrux/transforms/<name>.py`
2. Implement a dataclass with `name: str` and `apply(text: str) -> str`
3. The Transform protocol in `base.py` is structural — no inheritance needed
4. Add tests in `tests/test_transforms.py`

## Adding a Check Rule

1. Add the rule to `src/horcrux/check.py`
2. Add a test to `tests/test_check.py`
3. If the rule has an auto-fix path, add it to `src/horcrux/fix.py`

## PR checklist

- [ ] Tests added or updated
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src tests` clean
- [ ] README updated if user-visible behavior changed
- [ ] Commit messages are clear and atomic
