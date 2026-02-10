from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Literal, Mapping

from project_resolution_engine.internal.repositories.builtin import (
    DEFAULT_REPOSITORY_ID,
    RepoFactory,
)
from project_resolution_engine.internal.repositories.registry import (
    RepositoryRegistry,
    RepositoryRegistryError,
    build_repository_registry,
)
from project_resolution_engine.repository import ArtifactRepository


class RepositorySelectionError(RuntimeError):
    """
    Represents an error raised during repository selection.

    This class is a specific type of RuntimeError that is raised to indicate
    an issue occurred when attempting to select or work with a repository.
    It serves to distinguish repository selection errors from other runtime
    exceptions and can be used to encapsulate relevant context or information
    about the error.
    """

    pass


@dataclass(frozen=True, slots=True)
class RepositorySelection:
    """
    Represents a selection of a repository with associated metadata.

    This class is a data structure to encapsulate information regarding a specific repository
    selection. It includes the repository's unique identifier, its origin, and a factory
    responsible for creating or managing the repository instance.

    Attributes:
        repo_id: A unique string identifier for the repository.
        origin: The origin of the repository, specified as either "builtin" or "entrypoint".
        factory: An instance of RepoFactory used to create or manage the repository.
    """

    repo_id: str
    origin: Literal["builtin", "entrypoint"]
    factory: RepoFactory


def _select_repository(
    *, repo_id: str | None, registry: RepositoryRegistry
) -> RepositorySelection:
    """
    Determines and selects a repository based on the provided repository ID or a default
    identifier if none is given. Verifies the availability of the repository before selection.

    Parameters:
    repo_id: str | None
        Identifier of the repository to select. If None, the default repository ID is used.
    registry: RepositoryRegistry
        An object containing repository mappings, including built-in and
        entrypoint repositories.

    Returns:
    RepositorySelection
        An object representing the selected repository, its origin, and its factory function.

    Raises:
    RepositorySelectionError
        If the provided or default repository ID does not exist in the merged registry.
    """
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
        selection: RepositorySelection = _select_repository(
            repo_id=repo_id, registry=registry
        )
    except RepositoryRegistryError as e:
        raise RepositorySelectionError(str(e)) from e

    repo: ArtifactRepository = selection.factory(config=config)

    try:
        yield repo
    finally:
        repo.close()
