from __future__ import annotations

from collections.abc import Sequence, Mapping
from dataclasses import dataclass

from project_resolution_engine.internal.orchestration import (
    StrategyChainArtifactResolver,
    ArtifactCoordinator,
)
from project_resolution_engine.internal.util.strategy import load_strategies
from project_resolution_engine.model.keys import (
    IndexMetadataKey,
    CoreMetadataKey,
    WheelKey,
)
from project_resolution_engine.repository import (
    ArtifactRepository,
)
from project_resolution_engine.strategies import (
    BaseArtifactResolutionStrategy,
    IndexMetadataStrategy,
    CoreMetadataStrategy,
    WheelFileStrategy,
    StrategyCriticality,
    ResolutionStrategyConfig,
)

BUILTIN_STRATEGY_PACKAGE = "project_resolution_engine.internal.builtin_strategies"
STRATEGY_ENTRYPOINT_GROUP = "project_resolution_engine.strategies"
BUILTIN_STRATEGY_CONFIG_PACKAGE = (
    "project_resolution_engine.internal.builtin_strategy_configs"
)
STRATEGY_CONFIG_ENTRYPOINT_GROUP = "project_resolution_engine.strategy_configs"


# -------------------------
# service wiring
# -------------------------


@dataclass(frozen=True, slots=True)
class ResolutionServices:
    """
    Wires repositories and resolvers into coordinators for each artifact kind.

    The engine layer should depend on this object, not on raw repositories/strategies.
    """

    index_metadata: ArtifactCoordinator[IndexMetadataKey]
    core_metadata: ArtifactCoordinator[CoreMetadataKey]
    wheel: ArtifactCoordinator[WheelKey]


def build_services(
    *,
    repo: ArtifactRepository,
    index_metadata_strategies: Sequence[IndexMetadataStrategy],
    core_metadata_strategies: Sequence[CoreMetadataStrategy],
    wheel_strategies: Sequence[WheelFileStrategy],
) -> ResolutionServices:
    index_resolver: StrategyChainArtifactResolver[IndexMetadataKey] = (
        StrategyChainArtifactResolver(index_metadata_strategies)
    )
    core_resolver: StrategyChainArtifactResolver[CoreMetadataKey] = (
        StrategyChainArtifactResolver(core_metadata_strategies)
    )
    wheel_resolver: StrategyChainArtifactResolver[WheelKey] = (
        StrategyChainArtifactResolver(wheel_strategies)
    )

    return ResolutionServices(
        index_metadata=ArtifactCoordinator(repo=repo, resolver=index_resolver),
        core_metadata=ArtifactCoordinator(repo=repo, resolver=core_resolver),
        wheel=ArtifactCoordinator(repo=repo, resolver=wheel_resolver),
    )


# :: FeatureFlow | type=feature_start | name=service_loading
def load_services(
    *,
    repo: ArtifactRepository,
    strategy_configs_by_instance_id: (
        Mapping[str, ResolutionStrategyConfig] | None
    ) = None,
) -> ResolutionServices:
    """
    Discover -> plan -> topo sort -> instantiate strategies, then build service coordinators.

    Builtins are instantiated by default unless criticality resolves to ``DISABLED``.
    Entrypoint strategies are instantiated only when a config binds to them.

    strategy_configs_by_instance_id is the ONLY customization input here.
    """
    discovered: list[BaseArtifactResolutionStrategy] = load_strategies(
        strategy_package=BUILTIN_STRATEGY_PACKAGE,
        strategy_entrypoint_group=STRATEGY_ENTRYPOINT_GROUP,
        builtin_config_package=BUILTIN_STRATEGY_CONFIG_PACKAGE,
        config_entrypoint_group=STRATEGY_CONFIG_ENTRYPOINT_GROUP,
        raw_configs_by_instance_id=strategy_configs_by_instance_id,
    )

    if not discovered:
        raise RuntimeError("no strategies were loaded")

    # Criticality gating rule:
    # If any are IMPERATIVE, only IMPERATIVE strategies are allowed to participate.
    has_imperative = any(
        s.criticality is StrategyCriticality.IMPERATIVE for s in discovered
    )
    acceptable = (
        (StrategyCriticality.IMPERATIVE,)
        if has_imperative
        else (StrategyCriticality.REQUIRED, StrategyCriticality.OPTIONAL)
    )

    crit_rank = {
        StrategyCriticality.IMPERATIVE: 0,
        StrategyCriticality.REQUIRED: 1,
        StrategyCriticality.OPTIONAL: 2,
    }

    discovered = sorted(
        [s for s in discovered if s.criticality in acceptable],
        key=lambda s: (s.precedence, crit_rank[s.criticality], s.instance_id),
    )

    strats_by_type = {"index": [], "core": [], "wheel": []}

    for s in discovered:
        if isinstance(s, IndexMetadataStrategy):
            strats_by_type["index"].append(s)
        elif isinstance(s, CoreMetadataStrategy):
            strats_by_type["core"].append(s)
        elif isinstance(s, WheelFileStrategy):
            strats_by_type["wheel"].append(s)

    return build_services(
        repo=repo,
        index_metadata_strategies=strats_by_type["index"],
        core_metadata_strategies=strats_by_type["core"],
        wheel_strategies=strats_by_type["wheel"],
    )
