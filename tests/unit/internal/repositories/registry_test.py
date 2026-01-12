from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest


try:
    # Preferred import path in-repo.
    from project_resolution_engine.internal.repositories import registry as uut
except ModuleNotFoundError:  # pragma: no cover
    # Fallback for isolated execution of this file alongside registry.py.
    import registry as uut  # type: ignore[no-redef]


# ==============================================================================
# Test-local helpers
# ==============================================================================


def _make_factory(value: object) -> Callable[..., object]:
    def _factory(*, config=None) -> object:  # noqa: ANN001 - test helper
        return value

    return _factory


@dataclass(frozen=True)
class _FakeEntryPoint:
    name: str
    _loader: Callable[[], object]

    def load(self) -> object:
        return self._loader()


class _FakeEntryPoints:
    def __init__(self, eps: list[_FakeEntryPoint]) -> None:
        self._eps = eps

    def select(self, *, group: str) -> list[_FakeEntryPoint]:
        # The group filtering is performed by importlib.metadata, not our code.
        # We just return the list we were given for determinism.
        return self._eps


# ==============================================================================
# 7) Case matrix (mandatory)
# ==============================================================================

_VALIDATE_CASES = [
    # Covers: C000F001B0001
    dict(
        repo_id="r0",
        factory_obj=object(),
        exp_exc_substr="must load a callable factory; got object",
        covers=["C000F001B0001"],
    ),
    # Covers: C000F001B0002
    dict(
        repo_id="r1",
        factory_obj=type("NotAllowedClassFactory", (), {}),
        exp_exc_substr="must load a callable factory; got class NotAllowedClassFactory",
        covers=["C000F001B0002"],
    ),
    # Covers: C000F001B0003
    dict(
        repo_id="r2",
        factory_obj=(lambda: object()),  # no 'config' param
        exp_exc_substr="factory must accept keyword argument 'config'. Signature=",
        covers=["C000F001B0003"],
    ),
    # Covers: C000F001B0004
    dict(
        repo_id="r3",
        factory_obj=(lambda config, /: object()),  # positional-only 'config'
        exp_exc_substr="factory param 'config' must be keywordable. Signature=",
        covers=["C000F001B0004"],
    ),
    # Covers: C000F001B0005
    dict(
        repo_id="r4",
        factory_obj=(lambda *, config=None: object()),
        exp_exc_substr=None,
        covers=["C000F001B0005"],
    ),
]


_MERGED_CASES = [
    # Covers: C004M001B0001
    dict(
        builtins={"a": _make_factory("builtin")},
        externals={"a": _make_factory("external")},
        exp_exc_substr="duplicate repository ids found in builtins and entry points: ['a']",
        covers=["C004M001B0001"],
    ),
    # Covers: C004M001B0002
    dict(
        builtins={"a": _make_factory("builtin")},
        externals={"b": _make_factory("external")},
        exp_exc_substr=None,
        covers=["C004M001B0002"],
    ),
]


_LOAD_ENTRYPOINT_CASES = [
    # Covers: C000F002B0001, C000F002B0006
    dict(
        name="no-entrypoints",
        eps=[],
        exp_exc_substr=None,
        exp_empty=True,
        exp_single=None,
        covers=["C000F002B0001", "C000F002B0006"],
    ),
    # Covers: C000F002B0002, C000F002B0004, C000F002B0006
    dict(
        name="single-entrypoint",
        eps=[("repoA", _make_factory("A"))],
        exp_exc_substr=None,
        exp_empty=False,
        exp_single=("repoA", "A"),
        covers=["C000F002B0002", "C000F002B0004", "C000F002B0006"],
    ),
    # Covers: C000F002B0002, C000F002B0003, C000F002B0004, C000F002B0005
    dict(
        name="duplicate-entrypoints",
        eps=[("repoA", _make_factory("A1")), ("repoA", _make_factory("A2"))],
        exp_exc_substr="duplicate repository ids found in entry points group 'test.group': ['repoA']",
        exp_empty=None,
        exp_single=None,
        covers=["C000F002B0002", "C000F002B0003", "C000F002B0004", "C000F002B0005"],
    ),
]


_BUILD_REGISTRY_CASES = [
    # Covers: C000F003B0001
    dict(
        name="success",
        load_raises=None,
        covers=["C000F003B0001"],
    ),
    # Covers: C000F003B0002
    dict(
        name="load-raises",
        load_raises=uut.RepositoryEntrypointError("boom"),
        covers=["C000F003B0002"],
    ),
]


# ==============================================================================
# Tests
# ==============================================================================


def test_repofactory_call_body_is_ellipsis_and_returns_none() -> None:
    # Covers: C001M001B0001
    assert uut.RepoFactory.__call__(object(), config=None) is None


@pytest.mark.parametrize("case", _MERGED_CASES, ids=[c["covers"][0] for c in _MERGED_CASES])
def test_repository_registry_merged(case: dict) -> None:
    reg = uut.RepositoryRegistry(builtins=case["builtins"], externals=case["externals"])

    # Covers: C004M001B0001 / C004M001B0002
    if case["exp_exc_substr"] is not None:
        with pytest.raises(uut.RepositoryRegistryError) as ei:
            reg.merged()
        assert case["exp_exc_substr"] in str(ei.value)
        return

    merged = reg.merged()
    assert set(merged) == set(case["builtins"]) | set(case["externals"])
    assert merged["a"]() == "builtin"
    assert merged["b"]() == "external"


@pytest.mark.parametrize("case", _VALIDATE_CASES, ids=[c["covers"][0] for c in _VALIDATE_CASES])
def test_validate_repo_factory_callable(case: dict) -> None:
    # Covers: C000F001B0001..C000F001B0005
    if case["exp_exc_substr"] is not None:
        with pytest.raises(uut.RepositoryEntrypointError) as ei:
            uut._validate_repo_factory_callable(case["repo_id"], case["factory_obj"])
        assert case["exp_exc_substr"] in str(ei.value)
        return

    factory = uut._validate_repo_factory_callable(case["repo_id"], case["factory_obj"])
    assert factory is case["factory_obj"]


@pytest.mark.parametrize("case", _LOAD_ENTRYPOINT_CASES, ids=[c["name"] for c in _LOAD_ENTRYPOINT_CASES])
def test_load_entrypoint_repo_factories(monkeypatch: pytest.MonkeyPatch, case: dict) -> None:
    fake_eps = [
        _FakeEntryPoint(name=n, _loader=(lambda obj=o: obj))  # returns factory_obj
        for (n, o) in case["eps"]
    ]

    def _fake_entry_points() -> _FakeEntryPoints:
        return _FakeEntryPoints(fake_eps)

    # Mock external influence at call site.
    monkeypatch.setattr(uut, "entry_points", _fake_entry_points)

    # Covers: C000F002B0001..C000F002B0006
    if case["exp_exc_substr"] is not None:
        with pytest.raises(uut.RepositoryEntrypointError) as ei:
            uut._load_entrypoint_repo_factories(group="test.group")
        assert case["exp_exc_substr"] in str(ei.value)
        return

    factories = uut._load_entrypoint_repo_factories(group="test.group")

    if case["exp_empty"]:
        assert factories == {}
        return

    repo_id, exp_value = case["exp_single"]
    assert set(factories) == {repo_id}
    assert factories[repo_id]() == exp_value


@pytest.mark.parametrize("case", _BUILD_REGISTRY_CASES, ids=[c["name"] for c in _BUILD_REGISTRY_CASES])
def test_build_repository_registry(monkeypatch: pytest.MonkeyPatch, case: dict) -> None:
    # Mock external influences at call sites.
    monkeypatch.setattr(uut, "BUILTIN_REPOSITORY_FACTORIES", {"builtin": _make_factory("B")})
    monkeypatch.setattr(uut, "REPOSITORY_ENTRYPOINT_GROUP", "the.group")

    if case["load_raises"] is not None:

        def _raise(*, group: str):
            assert group == "the.group"
            raise case["load_raises"]

        monkeypatch.setattr(uut, "_load_entrypoint_repo_factories", _raise)

        # Covers: C000F003B0002
        with pytest.raises(uut.RepositoryEntrypointError) as ei:
            uut.build_repository_registry()
        assert "boom" in str(ei.value)
        return

    def _load(*, group: str):
        assert group == "the.group"
        return {"external": _make_factory("E")}

    monkeypatch.setattr(uut, "_load_entrypoint_repo_factories", _load)

    # Covers: C000F003B0001
    reg = uut.build_repository_registry()
    assert isinstance(reg, uut.RepositoryRegistry)
    assert set(reg.builtins) == {"builtin"}
    assert set(reg.externals) == {"external"}
