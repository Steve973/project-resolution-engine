from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Sequence

import pytest
from packaging.markers import Marker

from project_resolution_engine import api as uut
from project_resolution_engine.model.resolution import ResolutionMode
from unit.helpers import models_helper as mh

# =============================================================================
# Local minimal fakes (Result / criteria / information / parents)
# =============================================================================


@dataclass(slots=True)
class _FakeInfo:
    parent: Any


@dataclass(slots=True)
class _FakeCriterion:
    information: list[_FakeInfo]


@dataclass(slots=True)
class _FakeResult:
    mapping: dict[str, Any]
    criteria: dict[str, _FakeCriterion]


class _ComparableParent:
    """
    Parent object with a .name, but ALSO compares equal to the string name.
    This is necessary to drive the code path:

        if parent in deps_by_parent and child_name in wk_by_name:

    where deps_by_parent keys are strings.
    """

    def __init__(self, name: str, *, comparable_to_str: bool = True) -> None:
        self.name = name
        self._cmp = comparable_to_str

    def __hash__(self) -> int:
        return hash(self.name) if self._cmp else id(self)

    def __eq__(self, other: object) -> bool:
        if not self._cmp:
            return False
        if isinstance(other, str):
            return other == self.name
        return False


class _MappingProbe(Mapping[str, Any]):
    """
    Wrapper around a mapping that can:
      - delegate keys()/getitem()/iter/len
      - optionally assert if __contains__ is called (for short-circuit coverage)
    """

    def __init__(
        self, data: Mapping[str, Any], *, fail_on_contains: bool = False
    ) -> None:
        self._data = dict(data)
        self._fail_on_contains = fail_on_contains

    def __getitem__(self, k: str) -> Any:
        return self._data[k]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        if self._fail_on_contains:
            raise AssertionError(
                "__contains__ was evaluated, but should have short-circuited"
            )
        return key in self._data


# =============================================================================
# Shared patch: FakeWheelKey needs set_dependency_ids for api.py
# =============================================================================


@pytest.fixture(autouse=True)
def _patch_fake_wheelkey_set_dependency_ids() -> None:
    """
    api._apply_dependency_ids and ProjectResolutionEngine.resolve call WheelKey.set_dependency_ids(...).

    models_helper.FakeWheelKey does not define it, so we patch a minimal implementation
    onto the class for the duration of these tests.
    """
    if hasattr(mh.FakeWheelKey, "set_dependency_ids"):
        return

    def _set_dependency_ids(
        self: mh.FakeWheelKey, dep_wks: Sequence[mh.FakeWheelKey]
    ) -> None:
        object.__setattr__(
            self, "dependency_ids", frozenset(w.identifier for w in dep_wks)
        )

    setattr(mh.FakeWheelKey, "set_dependency_ids", _set_dependency_ids)


# =============================================================================
# 7) Case matrices (per contract)
# =============================================================================

_NORMALIZE_CASES: list[dict[str, Any]] = [
    {
        "id": "none",
        "strategy_configs": None,
        "expect": {},
        "raises": None,
        "covers": ["C000F001B0001"],
    },
    {
        "id": "empty_iterable",
        "strategy_configs": [],
        "expect": {},
        "raises": None,
        "covers": ["C000F001B0002"],
    },
    {
        "id": "missing_iid_and_name",
        "strategy_configs": [{}],
        "expect": None,
        "raises": "strategy config requires instance_id or strategy_name",
        "covers": ["C000F001B0003"],
    },
    {
        "id": "inject_instance_id",
        "strategy_configs": [
            {"strategy_name": "s1"},
            {"instance_id": "iid2", "strategy_name": "ignored"},
        ],
        "expect": {
            "s1": {"instance_id": "s1", "strategy_name": "s1"},
            "iid2": {"instance_id": "iid2", "strategy_name": "ignored"},
        },
        "raises": None,
        "covers": ["C000F001B0004"],
    },
]

_ROOTS_CASES: list[dict[str, Any]] = [
    {
        "id": "no_roots",
        "root_wheels": [],
        "env_marker_env": {"python_version": "3.11"},
        "expect_names": [],
        "covers": ["C000F002B0001"],
    },
    {
        "id": "marker_none_included",
        "root_wheels": [mh.ws(name="a", version="==1.0.0", marker=None)],
        "env_marker_env": {"python_version": "3.11"},
        "expect_names": ["a"],
        "covers": ["C000F002B0002"],
    },
    {
        "id": "marker_false_excluded",
        "root_wheels": [
            mh.ws(name="a", version="==1.0.0", marker=Marker('python_version < "3.0"'))
        ],
        "env_marker_env": {"python_version": "3.11"},
        "expect_names": [],
        "covers": ["C000F002B0003"],
    },
    {
        "id": "marker_true_included",
        "root_wheels": [
            mh.ws(name="a", version="==1.0.0", marker=Marker('python_version >= "3.0"'))
        ],
        "env_marker_env": {"python_version": "3.11"},
        "expect_names": ["a"],
        "covers": ["C000F002B0004"],
    },
]

_WK_BY_NAME_CASES: list[dict[str, Any]] = [
    {
        "id": "empty_mapping",
        "mapping": {},
        "expect_keys": [],
        "covers": ["C000F003B0001"],
    },
    {
        "id": "non_empty_mapping",
        "mapping": {
            "a": mh.FakeResolverCandidate(wheel_key=mh.wk(name="a")),
            "b": mh.FakeResolverCandidate(wheel_key=mh.wk(name="b")),
        },
        "expect_keys": ["a", "b"],
        "covers": ["C000F003B0002"],
    },
]

_DEPS_BY_PARENT_CASES: list[dict[str, Any]] = [
    {
        "id": "wk_empty_criteria_empty",
        "wk_by_name": {},
        "criteria": {},
        "expect": {},
        "covers": ["C000F004B0001", "C000F004B0003"],
    },
    {
        "id": "wk_nonempty_criteria_empty",
        "wk_by_name": {"a": mh.wk(name="a")},
        "criteria": {},
        "expect": {"a": set()},
        "covers": ["C000F004B0002", "C000F004B0003"],
    },
    {
        "id": "info_loop_zero",
        "wk_by_name": {"a": mh.wk(name="a")},
        "criteria": {"child": _FakeCriterion(information=[])},
        "expect": {"a": set()},
        "covers": ["C000F004B0004"],
    },
    {
        "id": "parent_none_continue",
        "wk_by_name": {"a": mh.wk(name="a"), "child": mh.wk(name="child")},
        "criteria": {"child": _FakeCriterion(information=[_FakeInfo(parent=None)])},
        "expect": {"a": set(), "child": set()},
        "covers": ["C000F004B0005"],
    },
    {
        "id": "parent_not_in_deps_short_circuit_contains_not_called",
        "wk_by_name": _MappingProbe({"a": mh.wk(name="a")}, fail_on_contains=True),
        "criteria": {
            "child": _FakeCriterion(
                information=[
                    _FakeInfo(parent=_ComparableParent("nope", comparable_to_str=False))
                ]
            )
        },
        "expect": {"a": set()},
        "covers": ["C000F004B0006"],
    },
    {
        "id": "parent_in_deps_child_not_in_wk",
        "wk_by_name": {"parent": mh.wk(name="parent")},
        "criteria": {
            "child": _FakeCriterion(
                information=[_FakeInfo(parent=_ComparableParent("parent"))]
            )
        },
        "expect": {"parent": set()},
        "covers": ["C000F004B0007"],
    },
    {
        "id": "parent_in_deps_child_in_wk_adds",
        "wk_by_name": {"parent": mh.wk(name="parent"), "child": mh.wk(name="child")},
        "criteria": {
            "child": _FakeCriterion(
                information=[_FakeInfo(parent=_ComparableParent("parent"))]
            )
        },
        "expect": {"parent": {"child"}, "child": set()},
        "covers": ["C000F004B0008"],
    },
]

_APPLY_DEPS_CASES: list[dict[str, Any]] = [
    {
        "id": "no_parents",
        "deps_by_parent": {},
        "wk_by_name": {},
        "expect_calls": {},
        "covers": ["C000F005B0001"],
    },
    {
        "id": "parent_empty_children",
        "deps_by_parent": {"p": set()},
        "wk_by_name": {"p": mh.wk(name="p")},
        "expect_calls": {"p": []},
        "covers": ["C000F005B0002"],
    },
    {
        "id": "parent_with_children_sorted",
        "deps_by_parent": {"p": {"b", "a"}},
        "wk_by_name": {
            "p": mh.wk(name="p"),
            "a": mh.wk(name="a"),
            "b": mh.wk(name="b"),
        },
        "expect_calls": {"p": ["a", "b"]},
        "covers": ["C000F005B0003"],
    },
]

_FMT_REQS_CASES: list[dict[str, Any]] = [
    {
        "id": "empty",
        "wheel_keys": [],
        "expect": "\n",
        "covers": ["C000F006B0001"],
    },
    {
        "id": "non_empty_sorted_joined",
        "wheel_keys": [
            mh.wk_reqtxt(name="b", version="1.0.0", tag="py3-none-any"),
            mh.wk_reqtxt(name="a", version="1.0.0", tag="py3-none-any"),
        ],
        "expect_order": ["a", "b"],
        "covers": ["C000F006B0002"],
    },
]

_RESOLVE_CASES: list[dict[str, Any]] = [
    {
        "id": "no_envs",
        "target_envs": [],
        "resolution_mode": ResolutionMode.REQUIREMENTS_TXT,
        "covers": ["C001M001B0001"],
    },
    {
        "id": "one_env_requirements_only",
        "target_envs": [
            mh.FakeResolutionEnv(
                identifier="env1",
                supported_tags=frozenset({"py3-none-any"}),
                marker_environment={"python_version": "3.11"},
            )
        ],
        "resolution_mode": ResolutionMode.REQUIREMENTS_TXT,
        "covers": ["C001M001B0002", "C001M001B0004"],
    },
    {
        "id": "one_env_resolved_wheels_mode",
        "target_envs": [
            mh.FakeResolutionEnv(
                identifier="env1",
                supported_tags=frozenset({"py3-none-any"}),
                marker_environment={"python_version": "3.11"},
            )
        ],
        "resolution_mode": ResolutionMode.RESOLVED_WHEELS,
        "covers": ["C001M001B0002", "C001M001B0003"],
    },
]


# =============================================================================
# 8) Tests
# =============================================================================


@pytest.mark.parametrize(
    "case", _NORMALIZE_CASES, ids=[c["id"] for c in _NORMALIZE_CASES]
)
def test_normalize_strategy_configs(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    if case["raises"] is not None:
        with pytest.raises(ValueError) as e:
            uut._normalize_strategy_configs(case["strategy_configs"])
        assert case["raises"] in str(e.value)
        return

    got = uut._normalize_strategy_configs(case["strategy_configs"])
    assert got == case["expect"]


@pytest.mark.parametrize("case", _ROOTS_CASES, ids=[c["id"] for c in _ROOTS_CASES])
def test_roots_for_env(case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: see case["covers"]

    # Patch the ResolverRequirement that _roots_for_env imports at call time.
    from project_resolution_engine.internal import resolvelib_types as rlt

    monkeypatch.setattr(
        rlt, "ResolverRequirement", mh.FakeResolverRequirement, raising=True
    )

    class _Env:
        def __init__(self, marker_environment: Mapping[str, str]) -> None:
            self.marker_environment = dict(marker_environment)

    params = mh.FakeResolutionParams(
        root_wheels=case["root_wheels"],
        target_environments=[],
    )
    env = _Env(case["env_marker_env"])

    roots = uut._roots_for_env(params, env)
    assert [r.wheel_spec.name for r in roots] == case["expect_names"]


@pytest.mark.parametrize(
    "case", _WK_BY_NAME_CASES, ids=[c["id"] for c in _WK_BY_NAME_CASES]
)
def test_wk_by_name_from_result(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    result = _FakeResult(mapping=case["mapping"], criteria={})
    got = uut._wk_by_name_from_result(result)  # type: ignore[arg-type]
    assert sorted(got.keys()) == case["expect_keys"]


@pytest.mark.parametrize(
    "case", _DEPS_BY_PARENT_CASES, ids=[c["id"] for c in _DEPS_BY_PARENT_CASES]
)
def test_deps_by_parent_from_result(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    wk_by_name = case["wk_by_name"]
    result = _FakeResult(mapping={}, criteria=case["criteria"])
    got = uut._deps_by_parent_from_result(result, wk_by_name)  # type: ignore[arg-type]
    assert got == case["expect"]


@pytest.mark.parametrize(
    "case", _APPLY_DEPS_CASES, ids=[c["id"] for c in _APPLY_DEPS_CASES]
)
def test_apply_dependency_ids(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Covers: see case["covers"]

    # Spy on set_dependency_ids calls on the specific parent keys.
    calls: dict[str, list[mh.FakeWheelKey]] = {}

    def _spy_set_dependency_ids(
        self: mh.FakeWheelKey, dep_wks: Sequence[mh.FakeWheelKey]
    ) -> None:
        calls[self.name] = list(dep_wks)
        object.__setattr__(
            self, "dependency_ids", frozenset(w.identifier for w in dep_wks)
        )

    # Patch the method on the class for this test.
    monkeypatch.setattr(
        mh.FakeWheelKey, "set_dependency_ids", _spy_set_dependency_ids, raising=True
    )

    deps_by_parent = case["deps_by_parent"]
    wk_by_name: MutableMapping[str, mh.FakeWheelKey] = dict(case["wk_by_name"])

    uut._apply_dependency_ids(deps_by_parent, wk_by_name)

    # Normalize to child-name lists for easier assertions.
    got_calls = {
        parent_name: [w.name for w in dep_wks] for parent_name, dep_wks in calls.items()
    }
    assert got_calls == case["expect_calls"]


@pytest.mark.parametrize(
    "case", _FMT_REQS_CASES, ids=[c["id"] for c in _FMT_REQS_CASES]
)
def test_format_requirements_text(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    if case["id"] == "empty":
        assert uut._format_requirements_text(case["wheel_keys"]) == case["expect"]
        return

    out = uut._format_requirements_text(case["wheel_keys"])
    assert out.endswith("\n")

    # Verify sort order by wheel key name within the formatted text.
    # Each req_txt_block contains a line starting with "<name> @ ..."
    lines = [ln for ln in out.splitlines() if " @ " in ln]
    names_in_order = [ln.split(" @ ", 1)[0].strip() for ln in lines]
    assert names_in_order == case["expect_order"]
    assert "\n\n" in out  # double-newline join between blocks


@pytest.mark.parametrize("case", _RESOLVE_CASES, ids=[c["id"] for c in _RESOLVE_CASES])
def test_project_resolution_engine_resolve(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Covers: see case["covers"]

    # ---- patch open_repository context manager ----
    from project_resolution_engine.internal.repositories import factory as repo_factory

    class _RepoCtx:
        def __init__(self, repo: object) -> None:
            self._repo = repo

        def __enter__(self) -> object:
            return self._repo

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    repo_obj = object()
    open_repo_calls: list[tuple[Any, Any]] = []

    def _open_repository(*, repo_id: Any, config: Any) -> _RepoCtx:
        open_repo_calls.append((repo_id, config))
        return _RepoCtx(repo_obj)

    monkeypatch.setattr(repo_factory, "open_repository", _open_repository, raising=True)

    # ---- patch load_services (imported at module scope in api.py) ----
    load_services_calls: list[dict[str, Any]] = []

    def _load_services(*, repo: Any, strategy_configs_by_instance_id: Any) -> object:
        load_services_calls.append(
            {"repo": repo, "configs": strategy_configs_by_instance_id}
        )
        return object()

    monkeypatch.setattr(uut, "load_services", _load_services, raising=True)

    # ---- patch internal resolvelib resolver ----
    from project_resolution_engine.internal import resolvelib as internal_resolvelib

    rl_calls: list[dict[str, Any]] = []

    def _rl_resolve(*, services: Any, env: Any, roots: Any) -> _FakeResult:
        rl_calls.append({"services": services, "env": env, "roots": roots})
        return _FakeResult(
            mapping={
                "a": mh.FakeResolverCandidate(
                    wheel_key=mh.wk_reqtxt(
                        name="a", version="1.0.0", tag="py3-none-any"
                    )
                ),
                "b": mh.FakeResolverCandidate(
                    wheel_key=mh.wk_reqtxt(
                        name="b", version="1.0.0", tag="py3-none-any"
                    )
                ),
            },
            criteria={},  # keep dependency graph empty for unit isolation
        )

    monkeypatch.setattr(internal_resolvelib, "resolve", _rl_resolve, raising=True)

    # ---- params ----
    params = mh.FakeResolutionParams(
        root_wheels=[],  # keep roots empty for resolve-branch focus
        target_environments=case["target_envs"],
        resolution_mode=case["resolution_mode"],
        repo_id="repo1",
        repo_config={"k": "v"},
        strategy_configs=[{"strategy_name": "s1"}],
    )

    res = uut.ProjectResolutionEngine.resolve(params)  # type: ignore[arg-type]

    # ---- assertions that validate the branches ----
    assert len(open_repo_calls) == 1
    assert len(load_services_calls) == 1

    # Config normalization must inject instance_id == strategy_name for "s1"
    assert "s1" in load_services_calls[0]["configs"]
    assert load_services_calls[0]["configs"]["s1"]["instance_id"] == "s1"

    if len(case["target_envs"]) == 0:
        # C001M001B0001
        assert rl_calls == []
        assert res.requirements_by_env == {}
        assert res.resolved_wheels_by_env == {}
        return

    # env loop >= 1 (C001M001B0002)
    assert len(rl_calls) == len(case["target_envs"])
    for env in case["target_envs"]:
        assert env.identifier in res.requirements_by_env
        assert res.requirements_by_env[env.identifier].endswith("\n")

    if case["resolution_mode"] is ResolutionMode.RESOLVED_WHEELS:
        # C001M001B0003
        assert set(res.resolved_wheels_by_env.keys()) == {
            e.identifier for e in case["target_envs"]
        }
        assert all(v == [] for v in res.resolved_wheels_by_env.values())
    else:
        # C001M001B0004
        assert res.resolved_wheels_by_env == {}
