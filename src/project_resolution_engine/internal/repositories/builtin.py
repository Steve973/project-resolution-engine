from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from project_resolution_engine.repository import ArtifactRepository

RepoFactory: TypeAlias = Callable[..., ArtifactRepository]


def _create_ephemeral(
    *, _config: Mapping[str, Any] | None = None
) -> ArtifactRepository:
    """
    Creates and returns an ephemeral artifact repository.

    This function initializes an instance of an ephemeral artifact repository,
    which is used to temporarily store artifacts without persisting them beyond
    the scope of its usage.

    Parameters:
    _config: Optional mapping of configuration settings used to set up the repository.

    Returns:
    ArtifactRepository: An instance of an ephemeral artifact repository.
    """
    from project_resolution_engine.internal.builtin_repository import (
        EphemeralArtifactRepository,
    )

    # Just create and return
    return EphemeralArtifactRepository()


# The name of the default repository
DEFAULT_REPOSITORY_ID = "ephemeral"

# Dictionary of the name of the factory to its factory function
BUILTIN_REPOSITORY_FACTORIES: dict[str, Callable[..., ArtifactRepository]] = {
    "ephemeral": _create_ephemeral,
}
