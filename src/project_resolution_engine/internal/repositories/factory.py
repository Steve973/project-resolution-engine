from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal, Mapping

from project_resolution_engine.internal.repositories.builtin import (
    DEFAULT_REPOSITORY_ID,
)
from project_resolution_engine.internal.repositories.registry import (
    RepoFactory,
    RepositoryRegistry,
    RepositoryRegistryError,
    build_repository_registry,
)
from project_resolution_engine.repository import ArtifactRepository


class RepositorySelectionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RepositorySelection:
    repo_id: str
    origin: Literal["builtin", "entrypoint"]
    factory: RepoFactory


def _select_repository(
    *, repo_id: str | None, registry: RepositoryRegistry
) -> RepositorySelection:
    rid = repo_id or DEFAULT_REPOSITORY_ID

    merged = registry.merged()
    if rid not in merged:
        raise RepositorySelectionError(
            f"unknown repository id {rid!r}. available={sorted(merged)}"
        )

    origin: Literal["builtin", "entrypoint"] = (
        "builtin" if rid in registry.builtins else "entrypoint"
    )
    return RepositorySelection(repo_id=rid, origin=origin, factory=merged[rid])


@contextmanager
def open_repository(
    *,
    repo_id: str | None,
    config: Mapping[str, Any] | None = None,
    registry: RepositoryRegistry | None = None,
) -> Iterator[ArtifactRepository]:
    """
    Create exactly one repository instance for the run and manage its lifecycle.

    Parameters:
      - repo_id: None means "use the default"
      - config: passed to the selected RepoFactory (keyword arg `config`)
      - registry: test seam. If provided, enable_entrypoints is ignored.
    """
    if registry is None:
        registry = build_repository_registry()

    try:
        selection: RepositorySelection = _select_repository(repo_id=repo_id, registry=registry)
    except RepositoryRegistryError as e:
        raise RepositorySelectionError(str(e)) from e

    repo: ArtifactRepository = selection.factory(config=config)

    try:
        yield repo
    finally:
        repo.close()
