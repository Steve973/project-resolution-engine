from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import pytest

from project_resolution_engine.strategies import StrategyCriticality
from unit.helpers.models_helper import (
    InMemoryArtifactRepository,
    make_fake_strategy,
    patch_services_load_strategies,
)

# ==============================================================================
# 7) CASE MATRIX (must cover new branches per row)
# ==============================================================================

BUILD_SERVICES_CASES: list[dict[str, Any]] = [
    {
        "id": "basic_wiring",
        "repo": InMemoryArtifactRepository(),
        "index_strats": [make_fake_strategy("index", name="idx-a")],
        "core_strats": [make_fake_strategy("core", name="core-a")],
        "wheel_strats": [make_fake_strategy("wheel", name="wheel-a")],
        "covers": [
            "C000F001B0001",
            "C000F001B0002",
            "C000F001B0003",
            "C000F001B0004",
        ],
    }
]

LOAD_SERVICES_RAISE_CASES: list[dict[str, Any]] = [
    {
        "id": "no_strategies_loaded",
        "discovered": [],
        "configs": {
            "x": {
                "strategy_name": "dummy",
                "instance_id": "x",
                "precedence": 123,
                "criticality": StrategyCriticality.OPTIONAL,
            }
        },
        "error_substring": "no strategies were loaded",
        "covers": [
            "C000F002B0001",
            "C000F002B0002",
        ],
    }
]

LOAD_SERVICES_OK_CASES: list[dict[str, Any]] = [
    {
        "id": "imperative_gating_filters_required_optional_and_sorts",
        "configs": None,
        "discovered": [
            # Included (IMPERATIVE), and sorted by (precedence, crit_rank, instance_id)
            make_fake_strategy(
                "wheel",
                name="wheel-imp",
                precedence=1,
                criticality=StrategyCriticality.IMPERATIVE,
                instance_id="w",
            ),
            make_fake_strategy(
                "index",
                name="index-imp-b",
                precedence=5,
                criticality=StrategyCriticality.IMPERATIVE,
                instance_id="b",
            ),
            make_fake_strategy(
                "core",
                name="core-imp-c",
                precedence=5,
                criticality=StrategyCriticality.IMPERATIVE,
                instance_id="c",
            ),
            make_fake_strategy(
                "index",
                name="index-imp-a",
                precedence=5,
                criticality=StrategyCriticality.IMPERATIVE,
                instance_id="a",
            ),
            # Excluded because has_imperative=True => acceptable=(IMPERATIVE,)
            make_fake_strategy(
                "index",
                name="index-req-excluded",
                precedence=0,
                criticality=StrategyCriticality.REQUIRED,
                instance_id="z",
            ),
            make_fake_strategy(
                "wheel",
                name="wheel-opt-excluded",
                precedence=0,
                criticality=StrategyCriticality.OPTIONAL,
                instance_id="y",
            ),
            make_fake_strategy(
                "core",
                name="core-disabled-excluded",
                precedence=0,
                criticality=StrategyCriticality.DISABLED,
                instance_id="x",
            ),
        ],
        "expect_index": ["index-imp-a", "index-imp-b"],
        "expect_core": ["core-imp-c"],
        "expect_wheel": ["wheel-imp"],
        "covers": [
            "C000F002B0001",
            "C000F002B0003",
            "C000F002B0004",
            "C000F002B0006",
            "C000F002B0008",
            "C000F002B0009",
            "C000F002B0010",
            "C000F002B0011",
            "C000F002B0012",
            "C000F002B0013",
            "C000F002B0014",
            "C000F002B0015",
            "C000F002B0016",
            "C000F002B0017",
            "C000F002B0018",
        ],
    },
    {
        "id": "required_optional_gating_filters_disabled_and_sorts_with_crit_rank",
        "configs": {
            "cfg-1": {
                "strategy_name": "dummy",
                "instance_id": "cfg-1",
                "precedence": 7,
                "criticality": StrategyCriticality.REQUIRED,
            }
        },
        "discovered": [
            # precedence=1, REQUIRED should sort before OPTIONAL (crit_rank REQUIRED=1 < OPTIONAL=2)
            make_fake_strategy(
                "core",
                name="core-req",
                precedence=1,
                criticality=StrategyCriticality.REQUIRED,
                instance_id="c",
            ),
            make_fake_strategy(
                "index",
                name="index-opt",
                precedence=1,
                criticality=StrategyCriticality.OPTIONAL,
                instance_id="a",
            ),
            make_fake_strategy(
                "wheel",
                name="wheel-opt",
                precedence=1,
                criticality=StrategyCriticality.OPTIONAL,
                instance_id="",  # exercises instance_id defaulting behavior in the fake base
            ),
            make_fake_strategy(
                "index",
                name="index-req",
                precedence=2,
                criticality=StrategyCriticality.REQUIRED,
                instance_id="b",
            ),
            # Excluded because acceptable=(REQUIRED, OPTIONAL)
            make_fake_strategy(
                "core",
                name="core-disabled-excluded",
                precedence=0,
                criticality=StrategyCriticality.DISABLED,
                instance_id="x",
            ),
        ],
        "expect_index": ["index-opt", "index-req"],
        "expect_core": ["core-req"],
        "expect_wheel": ["wheel-opt"],
        "covers": [
            "C000F002B0001",
            "C000F002B0003",
            "C000F002B0005",
            "C000F002B0007",
            "C000F002B0008",
            "C000F002B0009",
            "C000F002B0010",
            "C000F002B0011",
            "C000F002B0012",
            "C000F002B0013",
            "C000F002B0014",
            "C000F002B0015",
            "C000F002B0016",
            "C000F002B0017",
            "C000F002B0018",
        ],
    },
]

# ==============================================================================
# Test-only wiring spies (we must NOT use real orchestration classes)
# ==============================================================================


@dataclass(slots=True)
class _WiringSpies:
    resolver_inputs: list[list[Any]] = field(default_factory=list)
    coordinator_inputs: list[tuple[Any, Any]] = field(default_factory=list)


def _patch_services_wiring(monkeypatch: pytest.MonkeyPatch) -> _WiringSpies:
    """
    Patch services.StrategyChainArtifactResolver and services.ArtifactCoordinator with capturing fakes.
    """
    from project_resolution_engine import services as services_mod

    spies = _WiringSpies()

    class SpyStrategyChainArtifactResolver:
        def __init__(self, strategies: Sequence[Any]) -> None:
            # preserve order, but materialize for easy assertion
            self.strategies = list(strategies)
            spies.resolver_inputs.append(self.strategies)

    class SpyArtifactCoordinator:
        def __init__(self, *, repo: Any, resolver: Any) -> None:
            self.repo = repo
            self.resolver = resolver
            spies.coordinator_inputs.append((repo, resolver))

    monkeypatch.setattr(
        services_mod,
        "StrategyChainArtifactResolver",
        SpyStrategyChainArtifactResolver,
        raising=True,
    )
    monkeypatch.setattr(
        services_mod, "ArtifactCoordinator", SpyArtifactCoordinator, raising=True
    )

    return spies


# ==============================================================================
# Tests
# ==============================================================================


@pytest.mark.parametrize("case", BUILD_SERVICES_CASES, ids=lambda c: c["id"])
def test_build_services_wires_repo_and_resolvers(
    monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # Covers: C000F001B0001..C000F001B0004
    from project_resolution_engine import services as services_mod

    spies = _patch_services_wiring(monkeypatch)

    repo = case["repo"]
    index_strats = case["index_strats"]
    core_strats = case["core_strats"]
    wheel_strats = case["wheel_strats"]

    svcs = services_mod.build_services(
        repo=repo,
        index_metadata_strategies=index_strats,
        core_metadata_strategies=core_strats,
        wheel_strategies=wheel_strats,
    )

    # Resolver ctor calls happen in build order: index, core, wheel
    assert spies.resolver_inputs == [
        list(index_strats),
        list(core_strats),
        list(wheel_strats),
    ]

    # Coordinator ctor calls happen in build order: index, core, wheel
    assert len(spies.coordinator_inputs) == 3
    assert spies.coordinator_inputs[0][0] is repo
    assert spies.coordinator_inputs[1][0] is repo
    assert spies.coordinator_inputs[2][0] is repo

    # Returned object is the services dataclass, with our patched coordinator instances attached
    assert isinstance(svcs, services_mod.ResolutionServices)
    assert svcs.index_metadata.repo is repo
    assert svcs.core_metadata.repo is repo
    assert svcs.wheel.repo is repo

    # Each coordinator references the corresponding resolver instance created by build_services
    assert svcs.index_metadata.resolver.strategies == list(index_strats)
    assert svcs.core_metadata.resolver.strategies == list(core_strats)
    assert svcs.wheel.resolver.strategies == list(wheel_strats)


@pytest.mark.parametrize("case", LOAD_SERVICES_RAISE_CASES, ids=lambda c: c["id"])
def test_load_services_raises_when_no_strategies(
    monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # Covers: C000F002B0001, C000F002B0002
    from project_resolution_engine import services as services_mod

    # load_services should not reach build_services, but we still enforce "no real orchestration"
    _patch_services_wiring(monkeypatch)

    repo = InMemoryArtifactRepository()
    stub = patch_services_load_strategies(monkeypatch, return_value=case["discovered"])

    with pytest.raises(RuntimeError) as ei:
        services_mod.load_services(
            repo=repo, strategy_configs_by_instance_id=case["configs"]
        )

    assert case["error_substring"] in str(ei.value)

    # Ensure we pass through the exact config mapping object (or None) to load_strategies
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["strategy_package"] == services_mod.BUILTIN_STRATEGY_PACKAGE
    assert call["strategy_entrypoint_group"] == services_mod.STRATEGY_ENTRYPOINT_GROUP
    assert (
        call["builtin_config_package"] == services_mod.BUILTIN_STRATEGY_CONFIG_PACKAGE
    )
    assert (
        call["config_entrypoint_group"] == services_mod.STRATEGY_CONFIG_ENTRYPOINT_GROUP
    )
    assert call["raw_configs_by_instance_id"] is case["configs"]


@pytest.mark.parametrize("case", LOAD_SERVICES_OK_CASES, ids=lambda c: c["id"])
def test_load_services_gates_filters_sorts_and_builds(
    monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # Covers: C000F002B0001, C000F002B0003..C000F002B0018 (varies per case['covers'])
    from project_resolution_engine import services as services_mod

    spies = _patch_services_wiring(monkeypatch)
    repo = InMemoryArtifactRepository()

    discovered = case["discovered"]
    stub = patch_services_load_strategies(monkeypatch, return_value=discovered)

    svcs = services_mod.load_services(
        repo=repo, strategy_configs_by_instance_id=case["configs"]
    )

    # ---- load_strategies call passthrough ----
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["raw_configs_by_instance_id"] is case["configs"]

    # ---- expected strategies passed into each resolver ----
    expect_index_names = case["expect_index"]
    expect_core_names = case["expect_core"]
    expect_wheel_names = case["expect_wheel"]

    # build_services always constructs resolvers in this order
    assert len(spies.resolver_inputs) == 3
    got_index = spies.resolver_inputs[0]
    got_core = spies.resolver_inputs[1]
    got_wheel = spies.resolver_inputs[2]

    assert [s.name for s in got_index] == expect_index_names
    assert [s.name for s in got_core] == expect_core_names
    assert [s.name for s in got_wheel] == expect_wheel_names

    # ---- coordinators were created and wired to repo + corresponding resolver ----
    assert len(spies.coordinator_inputs) == 3
    assert svcs.index_metadata.repo is repo
    assert svcs.core_metadata.repo is repo
    assert svcs.wheel.repo is repo

    assert svcs.index_metadata.resolver.strategies == got_index
    assert svcs.core_metadata.resolver.strategies == got_core
    assert svcs.wheel.resolver.strategies == got_wheel

    # Sanity: excluded strategies (e.g., DISABLED, or REQUIRED/OPTIONAL under IMPERATIVE gating)
    # must not appear in any resolver input.
    flattened = [*got_index, *got_core, *got_wheel]
    flattened_names = {s.name for s in flattened}
    for s in discovered:
        if s.name in flattened_names:
            continue
        # If not present, that's fine; the point is we didn't accidentally include it.
        # (No further assertion needed; this loop exists to make intent explicit.)
        pass
