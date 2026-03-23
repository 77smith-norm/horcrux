# Adding a Harness Plugin

Horcrux can now load harness targets from a local Python file at runtime. You do
not need to edit `src/horcrux/targets/`, add imports to `__init__.py`, or wait
for a package release.

## What a plugin does

A harness plugin defines one or more `BaseTarget` subclasses and registers them
with `@register`. When a profile sets `harness_plugin`, Horcrux imports that
file before resolving `profile.harness`.

The plugin receives the same inputs as built-in harnesses:

1. `profile` — the validated `AgentProfile`
2. `source` — the canonical workspace after `source_root` resolution and
   `overrides` have already been applied

## Target Contract

Every plugin target must:

1. Subclass `BaseTarget`
2. Define a lowercase `harness_id` string
3. Decorate the class with `@register`
4. Implement `render() -> list[DiffusedFile]`

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

## Minimal Plugin

```python
from pathlib import Path
from typing import ClassVar

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register


@register
class BlobHarnessTarget(BaseTarget):
    harness_id: ClassVar[str] = "blob"

    def render(self) -> list[DiffusedFile]:
        return [
            DiffusedFile(
                relative_path=Path("PLUGIN.md"),
                content=self.source.read_text(Path("SOUL.md")),
                source_path=Path("SOUL.md"),
                transforms=("plugin-copy",),
            )
        ]
```

## Profile Example

```yaml
name: BlobAgent
harness: blob
harness_plugin: ~/horcrux-plugins/blob_harness.py
source_root: ~/horcrux-starter
overrides:
  USER.md: ~/clients/blob/USER.md
os: macos
output_dir: ~/agents/BlobAgent
model: gpt-5
voice_notes: "Lean and direct."
capabilities:
  - terminal
platform_notes: ""
```

`harness` must match the plugin target's `harness_id`.

## Authoring Notes

Use `self.source.read_text(Path("..."))` for canonical or overridden documents.
Use `source_path=None` for generated files with no canonical source. Use
`transforms` to leave a readable trail such as `("copy",)` or
`("plugin-render",)`.

`render()` must return a `list[DiffusedFile]`:

```python
@dataclass(frozen=True)
class DiffusedFile:
    relative_path: Path
    content: str
    source_path: Path | None
    transforms: tuple[str, ...]
```

## Test Workflow

1. Write the plugin file.
2. Create a profile that points to it with `harness_plugin`.
3. Run `horcrux diffuse <profile> --dry-run`.
4. Run `horcrux diffuse <profile> --force` after the preview looks right.
5. Add a focused test that imports the plugin with `load_plugin()` and a CLI test
   that diffuses through the plugin path.

## Security Model

`harness_plugin` executes arbitrary Python from a local file. This is
intentional. Horcrux only imports the path explicitly named in the profile; it
does not scan directories or auto-discover plugins. Treat plugin files with the
same trust level as any other Python code you run locally.
