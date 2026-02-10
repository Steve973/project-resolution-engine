from __future__ import annotations

import inspect
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Mapping

from project_resolution_engine.internal.repositories.builtin import (
    BUILTIN_REPOSITORY_FACTORIES, RepoFactory,
)
from project_resolution_engine.repository import (
    REPOSITORY_ENTRYPOINT_GROUP,
)


class RepositoryRegistryError(RuntimeError):
    pass


class RepositoryEntrypointError(RepositoryRegistryError):
    pass


@dataclass(frozen=True, slots=True)
class RepositoryRegistry:
    """
    Repository factories that are available to a single run.

    builtins: factories shipped with the library
    externals: factories discovered via entry points
    """

    builtins: Mapping[str, RepoFactory]
    externals: Mapping[str, RepoFactory]

    def merged(self) -> dict[str, RepoFactory]:
        dupes: set[str] = set(self.builtins).intersection(self.externals)
        if dupes:
            raise RepositoryRegistryError(
                f"duplicate repository ids found in builtins and entry points: {sorted(dupes)}"
            )
        merged: dict[str, RepoFactory] = dict(self.builtins)
        merged.update(self.externals)
        return merged


def _validate_repo_factory_callable(repo_id: str, factory_obj: object) -> RepoFactory:
    """
    Enforce a strict entry point contract.

    Entry points must load a callable that accepts a keywordable `config` parameter:
        def factory(*, config: Mapping[str, Any] | None = None) -> ArtifactRepository

    We do not accept classes here. If someone wants to expose a class, they can publish a
    small factory function that instantiates it.
    """
    if not callable(factory_obj):
        raise RepositoryEntrypointError(
            f"repo entry point '{repo_id}' must load a callable factory; got {type(factory_obj).__name__}"
        )

    if inspect.isclass(factory_obj):
        raise RepositoryEntrypointError(
            f"repo entry point '{repo_id}' must load a callable factory; got class {factory_obj.__name__}"
        )

    sig = inspect.signature(factory_obj)
    params = sig.parameters

    if "config" not in params:
        raise RepositoryEntrypointError(
            f"repo entry point '{repo_id}' factory must accept keyword argument 'config'. Signature={sig}"
        )

    p = params["config"]
    if p.kind not in (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        raise RepositoryEntrypointError(
            f"repo entry point '{repo_id}' factory param 'config' must be keywordable. Signature={sig}"
        )

    return factory_obj


def _load_entrypoint_repo_factories(*, group: str) -> dict[str, RepoFactory]:
    """
    Discover repository factories from entry points.

    Determinism rules:
      - entry point name is the repo id
      - duplicate ids within the same group are an error
      - loaded object must be a valid RepoFactory callable
    """
    factories: dict[str, RepoFactory] = {}
    dupes: set[str] = set()

    for ep in entry_points().select(group=group):
        repo_id = ep.name
        factory_obj = ep.load()
        factory = _validate_repo_factory_callable(repo_id, factory_obj)

        if repo_id in factories:
            dupes.add(repo_id)
            continue

        factories[repo_id] = factory

    if dupes:
        raise RepositoryEntrypointError(
            f"duplicate repository ids found in entry points group '{group}': {sorted(dupes)}"
        )

    return factories


def build_repository_registry() -> RepositoryRegistry:
    """
    Build the repository registry for a run.

    This is intentionally the only place that knows about REPOSITORY_ENTRYPOINT_GROUP.
    """
    externals: dict[str, RepoFactory] = _load_entrypoint_repo_factories(
        group=REPOSITORY_ENTRYPOINT_GROUP
    )

    return RepositoryRegistry(
        builtins=BUILTIN_REPOSITORY_FACTORIES, externals=externals
    )
