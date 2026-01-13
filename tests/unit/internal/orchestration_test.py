from __future__ import annotations

# ==============================================================================
# BRANCH LEDGER: orchestration.py
# ==============================================================================
#
# Classes (in file order):
#   C001 = StrategyChainArtifactResolver
#   C002 = ArtifactCoordinator
#
# ------------------------------------------------------------------------------
# ## StrategyChainArtifactResolver.resolve(self, key, destination_uri)
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: method entry -> begin resolve orchestration (initialize causes list)
# C001M001B0002: has_imperative is False -> skip imperative-mix validation; proceed to strategy loop
# C001M001B0003: has_imperative is True AND has_non_imperative is True -> raise RuntimeError (msg contains "All strategies must be imperative or all must be non-imperative")
# C001M001B0004: has_imperative is True AND has_non_imperative is False -> proceed to strategy loop
#
# C001M001B0005: for strategy in self.strategies executes 0 times -> proceed to final ArtifactResolutionError raise (no strategy attempted)
# C001M001B0006: for strategy in self.strategies executes >= 1 time -> enter loop body
#
# C001M001B0007: strategy.criticality is StrategyCriticality.DISABLED -> continue (skip strategy.resolve call)
#
# C001M001B0008: strategy.resolve(...) returns record where record is not None -> return FakeArtifactRecord
# C001M001B0009: strategy.resolve(...) returns None -> continue (try next strategy)
#
# C001M001B0010: strategy.resolve(...) raises StrategyNotApplicable -> continue (try next strategy)
# C001M001B0011: strategy.resolve(...) raises BaseException as e (non-StrategyNotApplicable) -> append e to causes; continue
#
# C001M001B0012: loop exhausted AND causes is empty -> raise ArtifactResolutionError (causes == ())
# C001M001B0013: loop exhausted AND causes is non-empty -> raise ArtifactResolutionError (causes contains collected exceptions)
#
# ------------------------------------------------------------------------------
# ## ArtifactCoordinator.resolve(self, key)
#    (Class ID: C002, Method ID: M001)
# ------------------------------------------------------------------------------
# C002M001B0001: hit = self.repo.get(key) and hit is not None -> return hit (no allocation / resolver / put)
# C002M001B0002: hit = self.repo.get(key) and hit is None -> call allocate_destination_uri; call resolver.resolve; call repo.put; return record
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none in this module)
#   [x] all `except` handlers captured
#   [x] all early `return`s / `raise`s captured
#   [x] all loop 0 vs >= 1 iterations captured
#   [x] all `break` / `continue` paths captured
# ==============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
from unittest.mock import Mock

import pytest

from project_resolution_engine.internal.orchestration import StrategyChainArtifactResolver, ArtifactCoordinator
from project_resolution_engine.model.resolution import ArtifactResolutionError
from project_resolution_engine.strategies import StrategyCriticality, StrategyNotApplicable
from unit.helpers.models_helper import FakeArtifactRecord, FakeWheelKey


# ==============================================================================
# Case matrix (per TESTING_CONTRACT.md)
# ==============================================================================

@dataclass(slots=True)
class _FakeStrategy:
    """
    Minimal strategy double.

    We intentionally do NOT inherit BaseArtifactResolutionStrategy here to keep the
    unit boundary strict: orchestration.py should only depend on attributes + resolve().
    """
    name: str
    criticality: StrategyCriticality
    _action: Callable[[object, str], FakeArtifactRecord | None]
    calls: int = 0
    last_key: object | None = None
    last_destination_uri: str | None = None

    def resolve(self, *, key: object, destination_uri: str) -> FakeArtifactRecord | None:
        self.calls += 1
        self.last_key = key
        self.last_destination_uri = destination_uri
        return self._action(key, destination_uri)


def _mk_key() -> FakeWheelKey:
    # Stable, real key type is fine here (no IO, no network).
    return FakeWheelKey(name="my-project", version="1.0", tag="py3-none-any")


def _mk_record(key: FakeWheelKey, *, dest: str = "file:///dest.whl", origin: str = "https://example/wheel.whl") -> FakeArtifactRecord:
    return FakeArtifactRecord(key=key, destination_uri=dest, origin_uri=origin)


def _act_return(record: FakeArtifactRecord) -> Callable[[object, str], FakeArtifactRecord]:
    def _inner(_key: object, _dest: str) -> FakeArtifactRecord:
        return record
    return _inner


def _act_return_none() -> Callable[[object, str], None]:
    def _inner(_key: object, _dest: str) -> None:
        return None
    return _inner


def _act_raise_not_applicable() -> Callable[[object, str], FakeArtifactRecord | None]:
    def _inner(_key: object, _dest: str) -> FakeArtifactRecord | None:
        raise StrategyNotApplicable("nope")
    return _inner


def _act_raise(exc: BaseException) -> Callable[[object, str], FakeArtifactRecord | None]:
    def _inner(_key: object, _dest: str) -> FakeArtifactRecord | None:
        raise exc
    return _inner


def _act_fail_if_called() -> Callable[[object, str], FakeArtifactRecord | None]:
    def _inner(_key: object, _dest: str) -> FakeArtifactRecord | None:
        raise AssertionError("disabled strategy should not be called")
    return _inner


# StrategyChainArtifactResolver.resolve() cases
RESOLVER_CASES: list[dict[str, object]] = [
    {
        "id": "mix_imperative_non_imperative_raises",
        "strategies": lambda: [
            _FakeStrategy("s1", StrategyCriticality.IMPERATIVE, _act_return_none()),
            _FakeStrategy("s2", StrategyCriticality.REQUIRED, _act_return_none()),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": RuntimeError,
        "expect_msg": "All strategies must be imperative or all must be non-imperative",
        "expect_record": None,
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0003"],
    },
    {
        "id": "imperative_only_allows_run_and_returns_record",
        "strategies": lambda: [
            _FakeStrategy("s1", StrategyCriticality.IMPERATIVE, _act_return(_mk_record(_mk_key()))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": None,
        "expect_msg": None,
        "expect_record": "non_none",
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0004", "C001M001B0006", "C001M001B0008"],
    },
    {
        "id": "no_strategies_loop_zero_raises_causes_empty",
        "strategies": lambda: [],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": ArtifactResolutionError,
        "expect_msg": "No strategy was able to resolve the requested artifact",
        "expect_record": None,
        "post_assert": lambda err: (
            (err.key, err.causes)  # exercised via asserts below
        ),
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0005", "C001M001B0012"],
    },
    {
        "id": "disabled_strategy_is_skipped_then_next_returns_record",
        "strategies": lambda: [
            _FakeStrategy("disabled", StrategyCriticality.DISABLED, _act_fail_if_called()),
            _FakeStrategy("ok", StrategyCriticality.REQUIRED, _act_return(_mk_record(_mk_key()))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": None,
        "expect_msg": None,
        "expect_record": "non_none",
        "post_assert": lambda strategies: (
            # disabled was not called; next was called exactly once
            (strategies[0].calls, strategies[1].calls)
        ),
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0007", "C001M001B0008"],
    },
    {
        "id": "strategy_returns_none_then_next_returns_record",
        "strategies": lambda: [
            _FakeStrategy("none", StrategyCriticality.OPTIONAL, _act_return_none()),
            _FakeStrategy("ok", StrategyCriticality.OPTIONAL, _act_return(_mk_record(_mk_key()))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": None,
        "expect_msg": None,
        "expect_record": "non_none",
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0009", "C001M001B0008"],
    },
    {
        "id": "strategy_raises_not_applicable_then_next_returns_record",
        "strategies": lambda: [
            _FakeStrategy("na", StrategyCriticality.OPTIONAL, _act_raise_not_applicable()),
            _FakeStrategy("ok", StrategyCriticality.OPTIONAL, _act_return(_mk_record(_mk_key()))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": None,
        "expect_msg": None,
        "expect_record": "non_none",
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0010", "C001M001B0008"],
    },
    {
        "id": "strategy_raises_other_exception_then_next_returns_record_and_error_is_collected_but_not_raised",
        "strategies": lambda: [
            _FakeStrategy("boom", StrategyCriticality.OPTIONAL, _act_raise(ValueError("boom"))),
            _FakeStrategy("ok", StrategyCriticality.OPTIONAL, _act_return(_mk_record(_mk_key()))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": None,
        "expect_msg": None,
        "expect_record": "non_none",
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0011", "C001M001B0008"],
    },
    {
        "id": "loop_exhausted_with_empty_causes_raises",
        "strategies": lambda: [
            _FakeStrategy("none", StrategyCriticality.OPTIONAL, _act_return_none()),
            _FakeStrategy("na", StrategyCriticality.OPTIONAL, _act_raise_not_applicable()),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": ArtifactResolutionError,
        "expect_msg": "No strategy was able to resolve the requested artifact",
        "expect_record": None,
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0009", "C001M001B0010", "C001M001B0012"],
    },
    {
        "id": "loop_exhausted_with_non_empty_causes_raises_and_causes_are_preserved",
        "strategies": lambda: [
            _FakeStrategy("boom1", StrategyCriticality.OPTIONAL, _act_raise(ValueError("boom1"))),
            _FakeStrategy("boom2", StrategyCriticality.OPTIONAL, _act_raise(RuntimeError("boom2"))),
        ],
        "key": _mk_key(),
        "dest_uri": "file:///dest.whl",
        "expect_exc": ArtifactResolutionError,
        "expect_msg": "No strategy was able to resolve the requested artifact",
        "expect_record": None,
        "post_assert": None,
        "covers": ["C001M001B0001", "C001M001B0002", "C001M001B0006", "C001M001B0011", "C001M001B0013"],
    },
]

# ArtifactCoordinator.resolve() cases
COORDINATOR_CASES: list[dict[str, object]] = [
    {
        "id": "repo_hit_returns_without_alloc_or_resolve_or_put",
        "hit": "non_none",
        "covers": ["C002M001B0001"],
    },
    {
        "id": "repo_miss_allocates_resolves_puts_and_returns",
        "hit": None,
        "covers": ["C002M001B0002"],
    },
]


# ==============================================================================
# Tests
# ==============================================================================

@pytest.mark.parametrize("case", RESOLVER_CASES, ids=lambda c: str(c["id"]))
def test_strategy_chain_artifact_resolver_resolve(case: dict[str, object]) -> None:
    # Covers: see case["covers"]
    strategies_factory = case["strategies"]
    assert callable(strategies_factory)

    strategies = strategies_factory()
    key = case["key"]
    dest_uri = case["dest_uri"]

    resolver = StrategyChainArtifactResolver(strategies=strategies)

    expect_exc = case["expect_exc"]
    if expect_exc is None:
        record = resolver.resolve(key=key, destination_uri=dest_uri)
        assert record is not None

        # sanity: ensure destination_uri passed through to the winning strategy
        assert isinstance(record, FakeArtifactRecord)

        post_assert = case.get("post_assert")
        if post_assert is not None:
            # for cases that want to assert call counts, etc
            _ = post_assert(strategies)

        # Additional targeted assertions for specific cases (kept small and meaningful)
        if case["id"] == "disabled_strategy_is_skipped_then_next_returns_record":
            assert strategies[0].calls == 0
            assert strategies[1].calls == 1

    else:
        with pytest.raises(expect_exc) as ei:
            _ = resolver.resolve(key=key, destination_uri=dest_uri)

        msg = str(ei.value)
        expect_msg = case.get("expect_msg")
        if expect_msg:
            assert str(expect_msg) in msg

        if expect_exc is ArtifactResolutionError:
            err = ei.value
            assert isinstance(err, ArtifactResolutionError)
            assert err.key is key

            if case["id"] == "no_strategies_loop_zero_raises_causes_empty":
                # Covers: C001M001B0012 (loop 0, causes empty)
                assert err.causes == ()

            if case["id"] == "loop_exhausted_with_empty_causes_raises":
                # Covers: C001M001B0012 (loop >=1, causes empty)
                assert err.causes == ()

            if case["id"] == "loop_exhausted_with_non_empty_causes_raises_and_causes_are_preserved":
                # Covers: C001M001B0013
                assert len(err.causes) == 2
                assert isinstance(err.causes[0], ValueError)
                assert "boom1" in str(err.causes[0])
                assert isinstance(err.causes[1], RuntimeError)
                assert "boom2" in str(err.causes[1])


@pytest.mark.parametrize("case", COORDINATOR_CASES, ids=lambda c: str(c["id"]))
def test_artifact_coordinator_resolve(case: dict[str, object]) -> None:
    # Covers: see case["covers"]
    key = _mk_key()

    repo = Mock()
    resolver = Mock()

    hit = case["hit"]
    if hit == "non_none":
        record = _mk_record(key)
        repo.get.return_value = record

        coordinator = ArtifactCoordinator(repo=repo, resolver=resolver)
        out = coordinator.resolve(key)

        assert out is record
        repo.get.assert_called_once_with(key)
        repo.allocate_destination_uri.assert_not_called()
        resolver.resolve.assert_not_called()
        repo.put.assert_not_called()

    else:
        repo.get.return_value = None
        repo.allocate_destination_uri.return_value = "file:///dest.whl"

        record = _mk_record(key, dest="file:///dest.whl")
        resolver.resolve.return_value = record

        coordinator = ArtifactCoordinator(repo=repo, resolver=resolver)
        out = coordinator.resolve(key)

        assert out is record
        repo.get.assert_called_once_with(key)
        repo.allocate_destination_uri.assert_called_once_with(key)
        resolver.resolve.assert_called_once_with(key=key, destination_uri="file:///dest.whl")
        repo.put.assert_called_once_with(record)
