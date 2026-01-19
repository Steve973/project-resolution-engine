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
        causes: list[BaseException] = []

        has_imperative = any(
            strategy.criticality is StrategyCriticality.IMPERATIVE
            for strategy in self.strategies
        )
        if has_imperative:
            has_non_imperative = any(
                strategy.criticality is not StrategyCriticality.IMPERATIVE
                for strategy in self.strategies
            )
            if has_non_imperative:
                raise RuntimeError(
                    "All strategies must be imperative or all must be non-imperative, but not both"
                )

        for strategy in self.strategies:
            if strategy.criticality is StrategyCriticality.DISABLED:
                logging.debug(f"strategy disabled: {strategy.name} key={key!r}")
                continue

            try:
                record = strategy.resolve(key=key, destination_uri=destination_uri)
                if record is None:
                    logging.debug(
                        f"strategy returned None: {strategy.name} key={key!r}"
                    )
                    continue
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

        raise ArtifactResolutionError(
            "No strategy was able to resolve the requested artifact",
            key=key,
            causes=tuple(causes),
        )


@dataclass(frozen=True, slots=True)
class ArtifactCoordinator(Generic[ArtifactKeyType]):
    repo: ArtifactRepository
    resolver: ArtifactResolver[ArtifactKeyType]

    def resolve(self, key: ArtifactKeyType) -> ArtifactRecord:
        hit = self.repo.get(key)
        if hit is not None:
            return hit

        dest_uri = self.repo.allocate_destination_uri(key)
        record = self.resolver.resolve(key=key, destination_uri=dest_uri)
        self.repo.put(record)
        return record
