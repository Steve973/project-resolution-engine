from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Generic, Sequence

from project_resolution_engine.model.keys import ArtifactKeyType
from project_resolution_engine.model.resolution import ArtifactResolutionError
from project_resolution_engine.repository import (
    ArtifactResolver,
    ArtifactRepository,
    ArtifactRecord,
)
from project_resolution_engine.strategies import (
    BaseArtifactResolutionStrategy,
    StrategyCriticality,
    StrategyNotApplicable,
)


@dataclass(frozen=True, slots=True)
class StrategyChainArtifactResolver(
    Generic[ArtifactKeyType], ArtifactResolver[ArtifactKeyType]
):
    """
    ArtifactResolver implementation that tries strategies in order.

    This is the replacement for the old "resolver guts":
    - no caching behavior
    - no index models
    - just acquisition orchestration
    """

    strategies: Sequence[BaseArtifactResolutionStrategy[ArtifactKeyType]]

    def resolve(self, key: ArtifactKeyType, destination_uri: str) -> ArtifactRecord:
        # :: FeatureStart | name=resolution_orchestration
        causes: list[BaseException] = []

        # Validate no mixing of imperative/non-imperative strategies
        criticalities = {s.criticality for s in self.strategies}
        if (
            StrategyCriticality.IMPERATIVE in criticalities
            and len(
                criticalities
                - {StrategyCriticality.IMPERATIVE, StrategyCriticality.DISABLED}
            )
            > 0
        ):
            # :: FeatureEnd | name=resolution_orchestration | outcome=invalid_strategy_config
            raise RuntimeError(
                "All strategies must be imperative or all must be non-imperative, but not both"
            )

        for strategy in self.strategies:
            if strategy.criticality is StrategyCriticality.DISABLED:
                logging.debug(f"strategy disabled: {strategy.name} key={key!r}")
                continue

            try:
                record: ArtifactRecord | None = strategy.resolve(
                    key=key, destination_uri=destination_uri
                )
                if record is None:
                    logging.debug(
                        f"strategy returned None: {strategy.name} key={key!r}"
                    )
                    continue
                # :: FeatureEnd | name=resolution_orchestration | outcome=success
                return record

            except StrategyNotApplicable:
                logging.debug(f"strategy not applicable: {strategy.name} key={key!r}")
                continue

            except BaseException as e:
                causes.append(e)
                logging.debug(
                    f"strategy failed: {strategy.name} key={key!r} err={type(e).__name__}: {e}"
                )
                continue

        # :: FeatureEnd | name=resolution_orchestration | outcome=artifact_resolution_failure
        raise ArtifactResolutionError(
            "No strategy was able to resolve the requested artifact",
            key=key,
            causes=tuple(causes),
        )


@dataclass(frozen=True, slots=True)
class ArtifactCoordinator(Generic[ArtifactKeyType]):
    """
    Coordinates the interaction between an artifact repository and a resolver. It
    looks for the artifact in the repository first, and if not found, it uses the
    resolver to fetch the artifact and stores it in the repository.

    ArtifactCoordinator is a generic class that supports resolving artifact records
    and storing them in a repository. It works with any artifact type provided
    through the type parameter ArtifactKeyType. The class ensures efficient querying
    by utilizing cached data when available and resolving new artifacts when necessary.

    Attributes:
        repo (ArtifactRepository): The artifact repository used for storing and
            retrieving artifact records.
        resolver (ArtifactResolver[ArtifactKeyType]): The resolver responsible for
            retrieving artifact records and storing them to a destination.

    Methods:
        resolve(key: ArtifactKeyType) -> ArtifactRecord:
            Resolves an artifact identified by the given key. First, it attempts to
            fetch the artifact from the repository cache. If the artifact is not
            found, it uses the resolver to fetch the artifact and stores it in the
            repository.
    """

    repo: ArtifactRepository
    resolver: ArtifactResolver[ArtifactKeyType]

    def resolve(self, key: ArtifactKeyType) -> ArtifactRecord:
        # :: FeatureStart | name=artifact_coordination
        hit = self.repo.get(key)
        if hit is not None:
            # :: FeatureEnd | name=artifact_coordination | outcome=cache_hit
            return hit

        dest_uri = self.repo.allocate_destination_uri(key)
        record = self.resolver.resolve(key=key, destination_uri=dest_uri)
        self.repo.put(record)
        # :: FeatureEnd | name=artifact_coordination | outcome=resolved_and_stored
        return record
