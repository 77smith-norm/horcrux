# Horcrux — Architecture

_Read this before adding or modifying any module. Agents: this is an invariant file. Do not violate the layer model._

---

## Layer Model

```
CLI (cli.py)
    │
    ├── Profile (profile.py)       — validated input config
    ├── Source (source.py)         — canonical workspace reader
    │
    └── Target (targets/)          — harness-specific renderer
            │
            ├── Transforms (transforms/)  — stateless text operations
            ├── Differ (differ.py)        — structural diff and output
            ├── Check (check.py)          — structural + tone analysis
            └── Fix (fix.py)              — interactive/auto repair
```

**Data flows one direction: CLI → Target → Transforms. No layer imports from a layer above it.**

---

## Module Ownership

| Module | Owns | Must NOT touch |
|--------|------|----------------|
| `cli.py` | Argument parsing, output formatting, exit codes | Business logic, file I/O beyond reading profile |
| `profile.py` | AgentProfile dataclass, YAML parsing, validation | Filesystem reads beyond the profile file itself |
| `source.py` | Reading canonical workspace files | Knowing about any target harness |
| `targets/` | Harness-specific rendering | CLI, registry, other targets |
| `transforms/` | Stateless text → text operations | Filesystem, profiles, any state |
| `differ.py` | Diff computation and output | Writing files, CLI args |
| `check.py` | Structural and tone analysis | Writing files, fixing issues |
| `fix.py` | Interactive and auto repair | Knowing about specific harnesses |
| `registry.py` | Agent registry persistence | All of the above |

---

## Harness Target Contract

Every harness target must:
1. Live in `src/horcrux/targets/<name>.py`
2. Subclass `BaseTarget` from `targets/base.py`
3. Implement `render() -> list[DiffusedFile]` and `harness_id: str`
4. Be decorated with `@register` from `targets/registry.py`
5. Be imported in `targets/__init__.py` (triggers self-registration)
6. Have tests in `tests/test_<name>_target.py`

**Adding a new harness requires zero changes to `cli.py`, `profile.py`, or any existing target.**

See `docs/adding-a-harness.md` for the full walkthrough.

---

## Quality Gates (enforced in CI)

```bash
uv run pytest            # all unit tests green (smoke excluded by default)
uv run ruff check src tests   # E, F, I, UP, C90 — max complexity 10
uv run ty check src      # type errors are build failures
```

**These are not suggestions. No commit lands that fails any of these.**

---

## Complexity Budget

- **Max McCabe complexity per function: 10** (enforced by ruff C901)
- **Max file length: use judgment** — if a file exceeds ~200 lines, ask whether it should be split
- **Max function length: ~30 lines** — not enforced mechanically, but a strong guideline
- If a function needs to be more complex, it must be decomposed into named helpers with clear responsibilities

---

## Type Discipline

- All public functions must have fully annotated signatures
- `Optional` pattern for platform-conditional imports: use `TYPE_CHECKING` guards or explicit `X | None` annotations rather than assigning `None` to a typed name
- `ty check src` must be clean — type errors are not acceptable in merged code

---

## Anti-Patterns (do not introduce)

- **Copy-paste logic across targets** — extract to a transform or a shared helper in `targets/base.py`
- **Conditional harness logic in `cli.py`** — use the target registry
- **God functions** — if a function does more than one thing, name and extract each thing
- **Untyped `dict` / `list` returns** — be specific: `dict[str, list[CheckIssue]]` not `dict`
- **Silent fallbacks that hide errors** — fail loudly; the caller decides how to handle it

---

_This document is the shape of the system. When in doubt, draw the layer diagram and check whether your change respects it._
