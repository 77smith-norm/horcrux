# Adding a New Harness to Horcrux

## What a harness target does

A harness target turns one validated `AgentProfile` plus the canonical source workspace into a list of `DiffusedFile` objects. The CLI does not special-case harnesses anymore. It asks the target registry for `profile.harness`, instantiates that target, and writes or diffs whatever `render()` returns.

That means a new harness should require only:

1. One target module under `src/horcrux/targets/`
2. One import in `src/horcrux/targets/__init__.py`
3. A profile YAML that names the new harness
4. Target-specific tests

No changes to `src/horcrux/profile.py` or `src/horcrux/cli.py` should be needed.

## Target contract

Every target must:

1. Subclass `BaseTarget`
2. Define a lowercase `harness_id` string that matches the profile `harness` field
3. Implement `render() -> list[DiffusedFile]`
4. Register itself with `@register`

`BaseTarget` provides:

```python
class BaseTarget(ABC):
    harness_id: ClassVar[str]

    def __init__(self, profile: AgentProfile, source: CanonicalWorkspace) -> None:
        self.profile = profile
        self.source = source

    @abstractmethod
    def render(self) -> list[DiffusedFile]:
        ...
```

## Steps

1. Create `src/horcrux/targets/<name>.py`
2. Import `BaseTarget` and `DiffusedFile` from `horcrux.targets.base`
3. Import `register` from `horcrux.targets.registry`
4. Subclass `BaseTarget`
5. Set `harness_id = "<name>"`
6. Implement `render()`
7. Add an import in `src/horcrux/targets/__init__.py`
8. Create a profile YAML with `harness: <name>`
9. Add tests in `tests/test_<name>_target.py`

## Example target

```python
from pathlib import Path

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register


@register
class CodexTarget(BaseTarget):
    harness_id = "codex"

    def render(self) -> list[DiffusedFile]:
        return [
            DiffusedFile(
                relative_path=Path("AGENTS.md"),
                content="# AGENTS.md\n\nCodex-specific context.\n",
                source_path=None,
                transforms=("render-codex-agents",),
            )
        ]
```

## Package registration

Targets self-register when their module is imported. Add the new target import to `src/horcrux/targets/__init__.py`:

```python
from horcrux.targets.codex import CodexTarget
```

If that import is missing, `get_target("codex")` will fail at runtime with `Unknown harness`.

## Profile YAML example

```yaml
name: CodexAgent
harness: codex
os: macos
output_dir: /tmp/codex-agent
model: gpt-5
voice_notes: "Lean and direct."
capabilities:
  - terminal
exclude_tools:
  - mdfind
platform_notes: ""
```

`profile.harness` is now a plain string. Validity comes from the runtime target registry, not from a closed enum in Pydantic.

## What `render()` must return

`render()` must return a `list[DiffusedFile]`. Each `DiffusedFile` describes one managed output file:

```python
@dataclass(frozen=True)
class DiffusedFile:
    relative_path: Path
    content: str
    source_path: Path | None
    transforms: tuple[str, ...]
```

Use:

1. `relative_path` for the file path under `output_dir`
2. `content` for the rendered text to write
3. `source_path` for canonical-source provenance, or `None` for generated files
4. `transforms` for an ordered label trail describing how the file was produced

## Testing expectations

Add at least:

1. A target-render test that checks the expected output files and important harness-specific content
2. A registry test if the harness adds unusual registration behavior
3. CLI coverage if the harness changes user-visible diffusion behavior

The main regression check is still: create a profile with `harness: <name>`, call the target, and confirm `render()` returns the right file set without any core-code edits.
