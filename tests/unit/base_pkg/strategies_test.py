from __future__ import annotations

from typing import Any

import pytest

from unit.helpers.models_helper import FakeIndexMetadataStrategy, FakeIndexMetadataKey, \
    ConcreteFakeBaseArtifactResolutionStrategy

# ==============================================================================
# 7) CASE MATRIX
# ==============================================================================

_POST_INIT_CASES: list[dict[str, Any]] = [
    {
        "desc": "instance_id defaults to name when empty",
        "strategy_kwargs": {"name": "pep691-simple", "instance_id": ""},
        "expected_instance_id": "pep691-simple",
        "covers": ["C005M001B0001"],
    },
    {
        "desc": "instance_id preserved when explicitly set",
        "strategy_kwargs": {"name": "pep691-simple", "instance_id": "custom-iid"},
        "expected_instance_id": "custom-iid",
        "covers": ["C005M001B0002"],
    },
]

_RESOLVE_CASES: list[dict[str, Any]] = [
    {
        "desc": "base resolve raises NotImplementedError",
        "covers": ["C005M002B0001"],
        "expected_exc_substr": "NotImplementedError",
    }
]


# ==============================================================================
# 8) TESTS
# ==============================================================================

@pytest.mark.parametrize(
    "case",
    [pytest.param(c, id=f"{c['covers'][0]}:{c['desc']}") for c in _POST_INIT_CASES],
)
def test_base_strategy_post_init_instance_id_defaulting(case: dict[str, Any]) -> None:
    # covers: C005M001B0001, C005M001B0002 (via parametrization)
    strat = FakeIndexMetadataStrategy(**case["strategy_kwargs"])
    assert strat.instance_id == case["expected_instance_id"]


@pytest.mark.parametrize(
    "case",
    [pytest.param(c, id=f"{c['covers'][0]}:{c['desc']}") for c in _RESOLVE_CASES],
)
def test_base_strategy_resolve_raises_not_implemented(case: dict[str, Any]) -> None:
    # covers: C005M002B0001
    strat = ConcreteFakeBaseArtifactResolutionStrategy(name="concrete")
    key = FakeIndexMetadataKey(project="demo-pkg")
    with pytest.raises(NotImplementedError) as excinfo:
        strat.resolve(key=key, destination_uri="mem://artifact/demo")

    # contract: assert substrings, not full stack traces
    assert case["expected_exc_substr"] in type(excinfo.value).__name__
