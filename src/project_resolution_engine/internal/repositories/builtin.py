from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from project_resolution_engine.repository import ArtifactRepository


class RepoFactory(Protocol):
    def __call__(self, *, config: Mapping[str, Any] | None = None) -> ArtifactRepository: ...


def _create_ephemeral(*, config: Mapping[str, Any] | None = None) -> ArtifactRepository:
    from project_resolution_engine.internal.builtin_repository import EphemeralArtifactRepository
    return EphemeralArtifactRepository()


DEFAULT_REPOSITORY_ID = "ephemeral"

BUILTIN_REPOSITORY_FACTORIES: dict[str, Callable[..., ArtifactRepository]] = {
    "ephemeral": _create_ephemeral,
}
