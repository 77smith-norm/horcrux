# Horcrux Multi-Client & Plugin Architecture Plan

Date: 2026-03-22
Status: Ready for Codex

The active plan is `docs/2026-03-22-multi-client-plan.md`.
All other plan docs in `docs/` are completed historical records — ignore them.

---

## Goal

Transform horcrux from a personal identity tool into a business-grade agent provisioning
tool. Three phases, each independently useful, each building on the last:

- **Phase 1** — Source independence: profiles declare their own source root. No personal
  workspace leakage. Enables client isolation.
- **Phase 2** — Document overrides: profiles can supply client-specific files for individual
  documents (USER.md, SOUL.md, etc.) that replace or merge with the canonical source.
- **Phase 3** — External harness plugins: new harnesses can be loaded from a Python file
  on disk without modifying horcrux's source or waiting for a PyPI release.

All phases: TCR+R discipline, `uv run pytest` green before every commit, `uv run ruff check
src tests` clean before every commit. The test suite must stay fully green throughout.

---

## Phase 1 — Source Independence

### What Changes

`AgentProfile` gains an optional `source_root` field. When set, horcrux loads canonical
documents from that directory instead of the default (`~/.openclaw/workspace` or
`HORCRUX_SOURCE_DIR`). All commands that touch the source workspace (`diffuse`, `check`,
`diff`, `fix`) respect it.

This is the unlock. Mayor Wheeler's profile points at `~/horcrux-starter`. Norman's
personal profiles omit `source_root` and continue using the default. Zero regression.

### Profile Change

```yaml
# Optional. If omitted, uses HORCRUX_SOURCE_DIR or ~/.openclaw/workspace
source_root: ~/horcrux-starter
```

### Model Change — `src/horcrux/profile.py`

Add `source_root: Path | None = None` to `AgentProfile`.

Add a validator that expands `~` and resolves the path (same pattern as `output_dir`).

`extra="forbid"` is currently set — this new field must be added or pydantic will reject
profiles that include it.

### Source Loader Change — `src/horcrux/source.py`

`load_canonical_workspace` already accepts an optional `root` argument. No change needed
to the function signature.

The change is in `cli.py`: wherever `default_source_root()` is called, instead call a new
helper `resolve_source_root(profile)` that returns `profile.source_root` if set, falling
back to `default_source_root()`.

```python
def resolve_source_root(profile: AgentProfile) -> Path:
    if profile.source_root is not None:
        return profile.source_root
    return default_source_root()
```

Put this in `source.py`. Simple, testable, single responsibility.

### CLI Change — `src/horcrux/cli.py`

Every command that loads a canonical workspace currently does:
```python
source = load_canonical_workspace(source_root=default_source_root())
```

Change each to:
```python
source = load_canonical_workspace(source_root=resolve_source_root(profile))
```

Commands affected: `diffuse`, `check`, `diff`, `fix`.

Also add `--source` / `-s` CLI flag as an override above the profile field:
```
horcrux diffuse profile.yaml --source ~/horcrux-starter
```

The precedence chain (highest to lowest):
1. `--source` CLI flag
2. `source_root` in profile YAML
3. `HORCRUX_SOURCE_DIR` env var
4. Default `~/.openclaw/workspace`

Implement this as `resolve_source_root(profile, cli_override=None)`.

### Tests — `tests/test_source.py` and `tests/test_profile.py`

**`test_profile.py` additions:**
- `test_profile_source_root_optional` — profile without `source_root` loads cleanly,
  `profile.source_root is None`
- `test_profile_source_root_expands_tilde` — `source_root: ~/foo` expands to absolute path
- `test_profile_source_root_absolute` — `/tmp/workspace` round-trips cleanly
- `test_profile_rejects_unknown_fields` — confirm `extra="forbid"` still works
  (regression guard — adding a new field can accidentally loosen this)

**`tests/test_source.py` additions:**
- `test_resolve_source_root_cli_override_wins` — cli_override beats profile.source_root
- `test_resolve_source_root_profile_wins_over_default` — profile.source_root beats default
- `test_resolve_source_root_falls_back_to_default` — None profile.source_root uses default

**CLI integration test additions (`tests/test_cli.py`):**
- `test_diffuse_respects_source_root_in_profile` — create a tmp source dir with minimal
  workspace files, write a profile pointing at it, run diffuse, confirm output came from
  the custom source not the real workspace
- `test_diffuse_source_flag_overrides_profile` — profile has `source_root: /tmp/a`,
  `--source /tmp/b` flag wins; output reflects `b`

### Commit Order for Phase 1

1. `feat: add source_root field to AgentProfile` — profile.py + tests
2. `feat: resolve_source_root helper with precedence chain` — source.py + tests
3. `feat: wire source_root into all CLI commands + --source flag` — cli.py + integration tests
4. `docs: update README and SKILL.md with source_root and --source docs`

---

## Phase 2 — Document Overrides

### What Changes

Profiles can declare per-document override paths. When a document is overridden, horcrux
reads from the override path instead of the canonical source. This is how you give Mayor
Wheeler a custom USER.md without touching the canonical workspace.

### Profile Change

```yaml
source_root: ~/horcrux-starter

overrides:
  USER.md: ~/horcrux-clients/medford-mayor/USER.md
  SOUL.md: ~/horcrux-clients/medford-mayor/SOUL.md
```

Keys are relative document paths (same as `CanonicalWorkspace` keys). Values are absolute
or `~`-prefixed paths to local files.

### Model Change — `src/horcrux/profile.py`

Add `overrides: dict[str, Path] = Field(default_factory=dict)` to `AgentProfile`.

Add a validator that expands `~` on all values:

```python
@field_validator("overrides", mode="before")
@classmethod
def _coerce_overrides(cls, value: object) -> object:
    if not isinstance(value, dict):
        return value
    return {k: Path(str(v)).expanduser() for k, v in value.items()}
```

### Source Loader Change — `src/horcrux/source.py`

Add `apply_overrides(workspace: CanonicalWorkspace, overrides: dict[str, Path]) -> CanonicalWorkspace`.

This function:
1. Starts with `workspace.documents` (a dict)
2. For each key in `overrides`:
   - Reads the file at the override path
   - Creates a `SourceDocument` with that content
   - Replaces (or adds) the entry in the documents dict
3. Returns a new `CanonicalWorkspace` with the merged documents

The override file must exist. If it doesn't, raise `FileNotFoundError` with a clear message:
```
Override for USER.md not found: /Users/norm/clients/foo/USER.md
```

Wire this into the CLI: after loading the canonical workspace, apply overrides from the
profile before passing the workspace to the target:

```python
source = load_canonical_workspace(source_root=resolve_source_root(profile, cli_source))
source = apply_overrides(source, profile.overrides)
target = get_target(profile.harness)(profile, source)
```

### Tests — `tests/test_source.py`

- `test_apply_overrides_replaces_document` — override USER.md, confirm workspace has new content
- `test_apply_overrides_adds_new_document` — override a path not in source, confirm it's added
- `test_apply_overrides_empty_overrides` — empty dict returns identical workspace
- `test_apply_overrides_missing_file_raises` — override path doesn't exist → FileNotFoundError
  with readable message
- `test_apply_overrides_expands_tilde` — tilde in profile is expanded before apply is called
  (already handled in validator, but add a round-trip test)

**CLI integration:**
- `test_diffuse_override_replaces_user_md` — tmp source dir + tmp override file,
  profile with `overrides: {USER.md: <override path>}`, diffuse → confirm USER.md in output
  contains override content, not canonical content

### Commit Order for Phase 2

1. `feat: add overrides field to AgentProfile` — profile.py + tests
2. `feat: apply_overrides — merge override files into canonical workspace` — source.py + tests
3. `feat: wire overrides into CLI diffuse/check/diff/fix` — cli.py + integration tests
4. `docs: update README and SKILL.md with overrides docs and example`

---

## Phase 3 — External Harness Plugins

### What Changes

Profiles can declare a `harness_plugin` path pointing to a Python file containing a
`BaseTarget` subclass decorated with `@register`. Horcrux imports it at runtime before
resolving the harness. New harnesses (Blob Harness, Hermes 2, whatever ships next month)
are one file and one profile field — no core changes, no PyPI release.

### Profile Change

```yaml
name: MayorWheelerBot
harness: blob
harness_plugin: ~/horcrux-plugins/blob_harness.py
source_root: ~/horcrux-starter
overrides:
  USER.md: ~/clients/medford-mayor/USER.md
```

### Plugin Contract

The plugin file must contain exactly one `BaseTarget` subclass decorated with `@register`.
The `harness_id` must match the `harness` field in the profile.

Example minimal plugin:

```python
from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register
from horcrux.transforms.copy import CopyTransform
from pathlib import Path

@register
class BlobHarnessTarget(BaseTarget):
    harness_id = "blob"

    def render(self) -> list[DiffusedFile]:
        return [
            self._render_from_source(Path("SOUL.md"), transforms=(CopyTransform(),)),
            self._render_from_source(Path("AGENTS.md"), transforms=(CopyTransform(),)),
        ]
```

### Implementation — `src/horcrux/targets/registry.py`

Add `load_plugin(plugin_path: Path) -> None`:

```python
import importlib.util
import sys

def load_plugin(plugin_path: Path) -> None:
    """Dynamically import a harness plugin file and register its targets."""
    if not plugin_path.exists():
        raise FileNotFoundError(
            f"harness_plugin not found: {plugin_path}\n"
            f"Check the path in your profile YAML."
        )
    spec = importlib.util.spec_from_file_location("_horcrux_plugin", plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin: {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_horcrux_plugin"] = module
    spec.loader.exec_module(module)
```

This uses the standard `importlib.util` pattern — no `exec()`, no `__import__` tricks.
The module is registered in `sys.modules` to avoid double-import issues.

### Model Change — `src/horcrux/profile.py`

Add `harness_plugin: Path | None = None` to `AgentProfile`.

Validator: expand `~`, same pattern as `output_dir`.

### CLI Change — `src/horcrux/cli.py`

In every command that calls `get_target(profile.harness)`, first call:

```python
if profile.harness_plugin is not None:
    load_plugin(profile.harness_plugin)
```

This must happen before `get_target()` so the plugin has time to register. Order matters.

### Security Note (document in code comment)

Plugin files execute arbitrary Python. This is intentional — it's the same trust model as
running any Python script. Horcrux is a local CLI tool run by the operator. The plugin path
must be explicitly set in the profile YAML, which the operator controls. No auto-discovery,
no path scanning. Document this clearly in the plugin docs.

### Tests — `tests/test_targets.py` or new `tests/test_plugin.py`

- `test_load_plugin_registers_harness` — write a tmp .py file with a minimal `@register`
  target, call `load_plugin()`, confirm `get_target("test-harness")` returns the class
- `test_load_plugin_missing_file_raises` — nonexistent path → FileNotFoundError with message
- `test_load_plugin_invalid_python_raises` — file with syntax error → ImportError or
  SyntaxError with readable message
- `test_profile_harness_plugin_optional` — profile without `harness_plugin` loads cleanly
- `test_profile_harness_plugin_expands_tilde` — `~/plugins/foo.py` expands correctly

**CLI integration:**
- `test_diffuse_with_harness_plugin` — write a tmp plugin file + profile, run diffuse via
  CliRunner, confirm output uses the plugin's render() output

### Commit Order for Phase 3

1. `feat: add harness_plugin field to AgentProfile` — profile.py + tests
2. `feat: load_plugin — dynamic harness import via importlib` — registry.py + tests
3. `feat: wire harness_plugin load into all CLI commands` — cli.py + integration tests
4. `docs: harness plugin authoring guide in docs/adding-a-harness.md`
5. `docs: update README and SKILL.md with plugin example`

---

## Quality Gates (All Phases)

Before every commit:
- `uv run pytest` — green (all existing tests must pass throughout)
- `uv run ruff check src tests` — clean
- `uv run ty check src` — clean

After all phases:
- `horcrux diffuse --help` shows `--source` flag
- Profile with `source_root`, `overrides`, and `harness_plugin` all validates cleanly
- Plugin load works end-to-end: write plugin → profile → diffuse → output uses plugin
- Smoke test against real Zocots workspace: `horcrux check` still passes with no issues
- Full suite: all passing

---

## AGENTS.md Update Required

After Phase 1 is complete, update `AGENTS.md` to note:
- Active plan is now `docs/2026-03-22-multi-client-plan.md`
- `resolve_source_root()` is now the canonical way to get the source root

---

## Compaction Recovery

1. `cat docs/2026-03-22-multi-client-plan.md`
2. `git log --oneline -20`
3. `uv run pytest` — confirm green
4. Identify which phase and commit step is next (check git log vs plan)
5. Resume. Do not restart. Do not re-implement committed work.
