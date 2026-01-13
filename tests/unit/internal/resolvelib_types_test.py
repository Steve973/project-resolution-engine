from __future__ import annotations
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, TypeAlias

import pytest
from packaging.markers import Marker
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

# Unit under test
import project_resolution_engine.internal.resolvelib_types as uut
from unit.helpers.models_helper import FakeWheelSpec, FakeWheelKey

# ==============================================================================
# BRANCH LEDGER: resolvelib_types (C000)
# ==============================================================================
# Source: /mnt/data/resolvelib_types.py  :contentReference[oaicite:0]{index=0}
# Spec:   /mnt/data/BRANCH_LEDGER_SPEC.md :contentReference[oaicite:1]{index=1}
#
# NOTE: This module has no control-flow branches (no if/match/try/loops). Per the
# spec, every callable still gets at least one “execution path” entry.
#
# ------------------------------------------------------------------------------
# ## Preference.__lt__(self, __other)
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: ... -> returns None (implicit; body is Ellipsis expression)
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.name(self)
#    (Class ID: C002, Method ID: M001)
# ------------------------------------------------------------------------------
# C002M001B0001: canonicalize_name(self.wheel_spec.name) -> returns canonicalized project name (str)
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.version(self)
#    (Class ID: C002, Method ID: M002)
# ------------------------------------------------------------------------------
# C002M002B0001: self.wheel_spec.version -> returns SpecifierSet | None
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.extras(self)
#    (Class ID: C002, Method ID: M003)
# ------------------------------------------------------------------------------
# C002M003B0001: self.wheel_spec.extras -> returns frozenset[str]
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.marker(self)
#    (Class ID: C002, Method ID: M004)
# ------------------------------------------------------------------------------
# C002M004B0001: self.wheel_spec.marker -> returns Marker | None
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.uri(self)
#    (Class ID: C002, Method ID: M005)
# ------------------------------------------------------------------------------
# C002M005B0001: self.wheel_spec.uri -> returns str | None
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.to_mapping(self, *args, **kwargs)
#    (Class ID: C002, Method ID: M006)
# ------------------------------------------------------------------------------
# C002M006B0001: {"wheel_spec": self.wheel_spec.to_mapping()} -> returns dict[str, Any] with wheel_spec mapping
#
# ------------------------------------------------------------------------------
# ## ResolverRequirement.from_mapping(cls, mapping, **_)
#    (Class ID: C002, Method ID: M007)
# ------------------------------------------------------------------------------
# C002M007B0001: cls(wheel_spec=WheelSpec.from_mapping(mapping["wheel_spec"])) -> returns ResolverRequirement
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.name(self)
#    (Class ID: C003, Method ID: M001)
# ------------------------------------------------------------------------------
# C003M001B0001: self.wheel_key.name -> returns str
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.version(self)
#    (Class ID: C003, Method ID: M002)
# ------------------------------------------------------------------------------
# C003M002B0001: self.wheel_key.version -> returns str
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.tag(self)
#    (Class ID: C003, Method ID: M003)
# ------------------------------------------------------------------------------
# C003M003B0001: self.wheel_key.tag -> returns str
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.requires_python(self)
#    (Class ID: C003, Method ID: M004)
# ------------------------------------------------------------------------------
# C003M004B0001: self.wheel_key.requires_python -> returns str | None
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.satisfied_tags(self)
#    (Class ID: C003, Method ID: M005)
# ------------------------------------------------------------------------------
# C003M005B0001: self.wheel_key.satisfied_tags -> returns frozenset[str]
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.dependency_ids(self)
#    (Class ID: C003, Method ID: M006)
# ------------------------------------------------------------------------------
# C003M006B0001: self.wheel_key.dependency_ids -> returns frozenset[str] | None
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.origin_uri(self)
#    (Class ID: C003, Method ID: M007)
# ------------------------------------------------------------------------------
# C003M007B0001: self.wheel_key.origin_uri -> returns str | None
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.marker(self)
#    (Class ID: C003, Method ID: M008)
# ------------------------------------------------------------------------------
# C003M008B0001: self.wheel_key.marker -> returns str | None
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.extras(self)
#    (Class ID: C003, Method ID: M009)
# ------------------------------------------------------------------------------
# C003M009B0001: self.wheel_key.extras -> returns frozenset[str] | None
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.to_mapping(self, *args, **kwargs)
#    (Class ID: C003, Method ID: M010)
# ------------------------------------------------------------------------------
# C003M010B0001: {"wheel_key": self.wheel_key.to_mapping()} -> returns dict[str, Any] with wheel_key mapping
#
# ------------------------------------------------------------------------------
# ## ResolverCandidate.from_mapping(cls, mapping, **_)
#    (Class ID: C003, Method ID: M011)
# ------------------------------------------------------------------------------
# C003M011B0001: cls(wheel_key=WheelKey.from_mapping(mapping["wheel_key"])) -> returns ResolverCandidate
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.starting(self)
#    (Class ID: C004, Method ID: M001)
# ------------------------------------------------------------------------------
# C004M001B0001: logging.log(logging.INFO, "Starting resolution...") -> calls logging.log(INFO, msg contains "Starting resolution")
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.starting_round(self, index)
#    (Class ID: C004, Method ID: M002)
# ------------------------------------------------------------------------------
# C004M002B0001: logging.log(logging.DEBUG, f"Starting round {index}") -> calls logging.log(DEBUG, msg contains f"Starting round {index}")
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.ending_round(self, index, state)
#    (Class ID: C004, Method ID: M003)
# ------------------------------------------------------------------------------
# C004M003B0001: logging.log(logging.DEBUG, f"Ending round {index}") -> calls logging.log(DEBUG, msg contains f"Ending round {index}")
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.ending(self, state)
#    (Class ID: C004, Method ID: M004)
# ------------------------------------------------------------------------------
# C004M004B0001: logging.log(logging.INFO, "Resolution complete.") -> calls logging.log(INFO, msg contains "Resolution complete.")
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.adding_requirement(self, requirement, parent)
#    (Class ID: C004, Method ID: M005)
# ------------------------------------------------------------------------------
# C004M005B0001: logging.log(logging.DEBUG, f"Adding requirement: {requirement}") -> calls logging.log(DEBUG, msg contains "Adding requirement:"
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.pinning(self, candidate)
#    (Class ID: C004, Method ID: M006)
# ------------------------------------------------------------------------------
# C004M006B0001: logging.log(logging.DEBUG, f"Pinning candidate: {candidate}") -> calls logging.log(DEBUG, msg contains "Pinning candidate:"
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.rejecting_candidate(self, criterion, candidate)
#    (Class ID: C004, Method ID: M007)
# ------------------------------------------------------------------------------
# C004M007B0001: logging.log(logging.DEBUG, f"Rejecting candidate: {candidate} (criterion={criterion})") -> calls logging.log(DEBUG, msg contains "Rejecting candidate:"
#
# ------------------------------------------------------------------------------
# ## ProjectResolutionReporter.resolving_conflicts(self, causes)
#    (Class ID: C004, Method ID: M008)
# ------------------------------------------------------------------------------
# C004M008B0001: logging.log(logging.DEBUG, f"Resolving conflicts: {causes}") -> calls logging.log(DEBUG, msg contains "Resolving conflicts:"
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured (none in module)
#   [x] all `match` / `case` arms captured (none in module)
#   [x] all `except` handlers captured (none in module)
#   [x] all early `return`s / `raise`s / `yield`s captured (none; only straight-line returns)
#   [x] all loop 0 vs >= 1 iterations captured (none in module)
#   [x] all `break` / `continue` paths captured (none in module)
# ==============================================================================
# ==============================================================================
# BRANCH LEDGER: resolvelib_types (C000)
# ==============================================================================
# NOTE: ledger intentionally kept as provided in this file previously.
# ==============================================================================

WheelKey: TypeAlias = FakeWheelKey
WheelSpec: TypeAlias = FakeWheelSpec


@pytest.fixture(autouse=True)
def _patch_resolvelib_types_model_classes(monkeypatch):
    monkeypatch.setattr(uut, "WheelKey", FakeWheelKey, raising=True)
    monkeypatch.setattr(uut, "WheelSpec", FakeWheelSpec, raising=True)


# ------------------------------------------------------------------------------
# Case matrix (required by TESTING_CONTRACT)
# ------------------------------------------------------------------------------

_REQ_CASES: list[dict[str, object]] = [
    {
        "id": "versioned",
        "wheel_spec": FakeWheelSpec(
            name="My_Project",
            version=SpecifierSet(">=1,<2"),
            extras=frozenset({"a", "b"}),
            marker=Marker('python_version < "4"'),
            uri=None,
        ),
        "expected_name": canonicalize_name("My_Project"),
        "covers": [
            "C002M001B0001",
            "C002M002B0001",
            "C002M003B0001",
            "C002M004B0001",
            "C002M005B0001",
            "C002M006B0001",
            "C002M007B0001",
        ],
    },
    {
        "id": "uri_only",
        "wheel_spec": FakeWheelSpec(
            name="SomePkg",
            version=None,
            extras=frozenset(),
            marker=None,
            uri="https://example.invalid/somepkg-1.2.3-py3-none-any.whl",
        ),
        "expected_name": canonicalize_name("SomePkg"),
        "covers": [
            "C002M001B0001",
            "C002M002B0001",
            "C002M003B0001",
            "C002M004B0001",
            "C002M005B0001",
            "C002M006B0001",
            "C002M007B0001",
        ],
    },
]

_CANDIDATE_CASES: list[dict[str, object]] = [
    {
        "id": "full_fields",
        "wheel_key": FakeWheelKey(
            name="my-project",
            version="1.2.3",
            tag="py3-none-any",
            requires_python=">=3.10",
            satisfied_tags=frozenset({"py3-none-any", "cp311-cp311-manylinux_x86_64"}),
            dependency_ids=frozenset({"dep-a-0.1-py3-none-any", "dep-b-2.0-py3-none-any"}),
            origin_uri="https://example.invalid/my_project-1.2.3-py3-none-any.whl",
            marker='python_version >= "3.10"',
            extras=frozenset({"extra1", "extra2"}),
        ),
        "covers": [
            "C003M001B0001",
            "C003M002B0001",
            "C003M003B0001",
            "C003M004B0001",
            "C003M005B0001",
            "C003M006B0001",
            "C003M007B0001",
            "C003M008B0001",
            "C003M009B0001",
            "C003M010B0001",
            "C003M011B0001",
        ],
    },
    {
        "id": "minimal_fields",
        "wheel_key": FakeWheelKey(
            name="another-project",
            version="0.0.1",
            tag="py3-none-any",
            requires_python=None,
            satisfied_tags=frozenset(),
            dependency_ids=None,
            origin_uri=None,
            marker=None,
            extras=None,
        ),
        "covers": [
            "C003M001B0001",
            "C003M002B0001",
            "C003M003B0001",
            "C003M004B0001",
            "C003M005B0001",
            "C003M006B0001",
            "C003M007B0001",
            "C003M008B0001",
            "C003M009B0001",
            "C003M010B0001",
            "C003M011B0001",
        ],
    },
]


def _capture_logging_calls(monkeypatch) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []

    def _fake_log(level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        # Keep only what the unit under test controls: level and message.
        calls.append((level, msg))

    monkeypatch.setattr(uut.logging, "log", _fake_log)
    return calls


@dataclass(frozen=True)
class _ReporterCallCase:
    id: str
    call: Callable[[uut.ProjectResolutionReporter], None]
    expected_level: int
    expected_msg_substr: str
    covers: list[str]


_REPORTER_CALL_CASES: list[_ReporterCallCase] = [
    _ReporterCallCase(
        id="starting",
        call=lambda r: r.starting(),
        expected_level=logging.INFO,
        expected_msg_substr="Starting resolution",
        covers=["C004M001B0001"],
    ),
    _ReporterCallCase(
        id="starting_round",
        call=lambda r: r.starting_round(7),
        expected_level=logging.DEBUG,
        expected_msg_substr="Starting round 7",
        covers=["C004M002B0001"],
    ),
    _ReporterCallCase(
        id="ending_round",
        call=lambda r: r.ending_round(9, object()),  # state unused by implementation
        expected_level=logging.DEBUG,
        expected_msg_substr="Ending round 9",
        covers=["C004M003B0001"],
    ),
    _ReporterCallCase(
        id="ending",
        call=lambda r: r.ending(object()),  # state unused by implementation
        expected_level=logging.INFO,
        expected_msg_substr="Resolution complete",
        covers=["C004M004B0001"],
    ),
    _ReporterCallCase(
        id="adding_requirement",
        call=lambda r: r.adding_requirement(object(), object()),
        expected_level=logging.DEBUG,
        expected_msg_substr="Adding requirement:",
        covers=["C004M005B0001"],
    ),
    _ReporterCallCase(
        id="pinning",
        call=lambda r: r.pinning(object()),
        expected_level=logging.DEBUG,
        expected_msg_substr="Pinning candidate:",
        covers=["C004M006B0001"],
    ),
    _ReporterCallCase(
        id="rejecting_candidate",
        call=lambda r: r.rejecting_candidate(object(), object()),  # criterion/candidate stringified
        expected_level=logging.DEBUG,
        expected_msg_substr="Rejecting candidate:",
        covers=["C004M007B0001"],
    ),
    _ReporterCallCase(
        id="resolving_conflicts",
        call=lambda r: r.resolving_conflicts([object()]),  # causes stringified
        expected_level=logging.DEBUG,
        expected_msg_substr="Resolving conflicts:",
        covers=["C004M008B0001"],
    ),
]


# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------


def test_preference_dunder_lt_executes() -> None:
    # Covers: C001M001B0001
    # The Protocol method body is `...` (Ellipsis expression), which returns None if executed.
    assert uut.Preference.__lt__(object(), object()) is None


@pytest.mark.parametrize("case", _REQ_CASES, ids=[c["id"] for c in _REQ_CASES])
def test_resolver_requirement_properties_and_mapping(case: dict[str, object]) -> None:
    # Covers: C002M001B0001, C002M002B0001, C002M003B0001, C002M004B0001, C002M005B0001,
    #         C002M006B0001, C002M007B0001
    ws = case["wheel_spec"]
    assert isinstance(ws, FakeWheelSpec)

    rr = uut.ResolverRequirement(wheel_spec=ws)

    assert rr.name == case["expected_name"]
    assert rr.version == ws.version
    assert rr.extras == ws.extras
    assert rr.marker == ws.marker
    assert rr.uri == ws.uri

    mapping = rr.to_mapping()
    assert isinstance(mapping, dict)
    assert "wheel_spec" in mapping
    assert isinstance(mapping["wheel_spec"], dict)

    rr2 = uut.ResolverRequirement.from_mapping(mapping)
    assert rr2 == rr


@pytest.mark.parametrize("case", _CANDIDATE_CASES, ids=[c["id"] for c in _CANDIDATE_CASES])
def test_resolver_candidate_properties_and_mapping(case: dict[str, object]) -> None:
    # Covers: C003M001B0001, C003M002B0001, C003M003B0001, C003M004B0001, C003M005B0001,
    #         C003M006B0001, C003M007B0001, C003M008B0001, C003M009B0001, C003M010B0001,
    #         C003M011B0001
    wk = case["wheel_key"]
    assert isinstance(wk, FakeWheelKey)

    cand = uut.ResolverCandidate(wheel_key=wk)

    assert cand.name == wk.name
    assert cand.version == wk.version
    assert cand.tag == wk.tag
    assert cand.requires_python == wk.requires_python
    assert cand.satisfied_tags == wk.satisfied_tags
    assert cand.dependency_ids == wk.dependency_ids
    assert cand.origin_uri == wk.origin_uri
    assert cand.marker == wk.marker
    assert cand.extras == wk.extras

    mapping = cand.to_mapping()
    assert isinstance(mapping, dict)
    assert "wheel_key" in mapping
    assert isinstance(mapping["wheel_key"], dict)

    cand2 = uut.ResolverCandidate.from_mapping(mapping)
    assert cand2 == cand


@pytest.mark.parametrize("case", _REPORTER_CALL_CASES, ids=[c.id for c in _REPORTER_CALL_CASES])
def test_project_resolution_reporter_logging(monkeypatch, case: _ReporterCallCase) -> None:
    # Covers: one of C004M001B0001..C004M008B0001 (per parametrized case)
    calls = _capture_logging_calls(monkeypatch)

    reporter = uut.ProjectResolutionReporter()
    case.call(reporter)

    assert len(calls) == 1
    level, msg = calls[0]
    assert level == case.expected_level
    assert case.expected_msg_substr in msg
