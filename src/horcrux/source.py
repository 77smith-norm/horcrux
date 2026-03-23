"""Canonical workspace loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from horcrux.profile import AgentProfile

DEFAULT_SOURCE_ROOT = Path("/Users/norm/.openclaw/workspace")
SOURCE_ROOT_ENV_VAR = "HORCRUX_SOURCE_DIR"
ROOT_DOCUMENTS = (
    Path("SOUL.md"),
    Path("AGENTS.md"),
    Path("HEARTBEAT.md"),
    Path("BOUNDARIES.md"),
    Path("TOOLS.md"),
    Path("MEMORY.md"),
    Path("IDENTITY.md"),
    Path("USER.md"),
)


@dataclass(frozen=True)
class SourceDocument:
    """A source document loaded from the canonical workspace."""

    relative_path: Path
    content: str


@dataclass(frozen=True)
class CanonicalWorkspace:
    """Canonical source workspace documents."""

    root: Path
    documents: dict[Path, SourceDocument]

    def read_text(self, relative_path: Path | str) -> str:
        path = Path(relative_path)
        return self.documents[path].content

    def has_document(self, relative_path: Path | str) -> bool:
        return Path(relative_path) in self.documents

    def list_paths(self) -> tuple[Path, ...]:
        return tuple(sorted(self.documents))


def default_source_root() -> Path:
    """Return the canonical workspace root, optionally overridden by env var."""

    override = os.environ.get(SOURCE_ROOT_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_SOURCE_ROOT


def resolve_source_root(
    profile: AgentProfile,
    cli_override: Path | str | None = None,
) -> Path:
    """Resolve the canonical workspace root from CLI, profile, or defaults."""

    if cli_override is not None:
        return Path(cli_override).expanduser()
    if profile.source_root is not None:
        return profile.source_root
    return default_source_root()


def apply_overrides(
    workspace: CanonicalWorkspace,
    overrides: dict[str, Path],
) -> CanonicalWorkspace:
    """Return a canonical workspace with per-document overrides applied."""

    if not overrides:
        return workspace

    documents = workspace.documents.copy()
    for relative_path_str, override_path in overrides.items():
        relative_path = Path(relative_path_str)
        if not override_path.exists():
            raise FileNotFoundError(f"Override for {relative_path} not found: {override_path}")
        documents[relative_path] = SourceDocument(
            relative_path=relative_path,
            content=override_path.read_text(encoding="utf-8"),
        )

    return CanonicalWorkspace(root=workspace.root, documents=documents)


def load_canonical_workspace(root: Path | str | None = None) -> CanonicalWorkspace:
    """Load the standard canonical workspace files from a directory."""

    workspace_root = Path(root) if root is not None else default_source_root()
    if not workspace_root.exists():
        raise FileNotFoundError(f"Source root not found: {workspace_root}")
    if not workspace_root.is_dir():
        raise NotADirectoryError(f"Source root is not a directory: {workspace_root}")
    documents: dict[Path, SourceDocument] = {}

    for relative_path in ROOT_DOCUMENTS:
        document_path = workspace_root / relative_path
        documents[relative_path] = SourceDocument(
            relative_path=relative_path,
            content=document_path.read_text(encoding="utf-8"),
        )

    refs_dir = workspace_root / "refs"
    for ref_path in sorted(refs_dir.glob("*.md")):
        relative_path = ref_path.relative_to(workspace_root)
        documents[relative_path] = SourceDocument(
            relative_path=relative_path,
            content=ref_path.read_text(encoding="utf-8"),
        )

    return CanonicalWorkspace(root=workspace_root, documents=documents)
