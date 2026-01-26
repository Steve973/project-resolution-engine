from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from unittest.mock import Mock

import pytest

import project_resolution_engine.internal.repositories.factory as factory

# ==============================================================================
# CASE MATRIX
# ==============================================================================


@dataclass(frozen=True, slots=True)
class _RegistryStub:
    """Minimal stub for RepositoryRegistry.

    This is a unit-test helper, not a test case class.
    """

    merged_impl: Callable[[], dict[str, Any]]
    builtins: set[str]

    def merged(self) -> dict[str, Any]:
        return self.merged_impl()


@dataclass(frozen=True, slots=True)
class _RepoStub:
    close_mock: Mock

    def close(self) -> None:
        self.close_mock()


SELECT_REPOSITORY_CASES_SUCCESS = [
    {
        "id": "explicit_repo_id_builtin",
        "repo_id": "r1",
        "default_repo_id": "default",
        "merged": {"r1": "factory_r1"},
        "builtins": {"r1"},
        "expect_repo_id": "r1",
        "expect_origin": "builtin",
        "expect_factory": "factory_r1",
        "covers": [
            "C000F001B0001",
            "C000F001B0003",
            "C000F001B0005",
            "C000F001B0006",
        ],
    },
    {
        "id": "default_repo_id_entrypoint",
        "repo_id": None,
        "default_repo_id": "default",
        "merged": {"default": "factory_default"},
        "builtins": set(),
        "expect_repo_id": "default",
        "expect_origin": "entrypoint",
        "expect_factory": "factory_default",
        "covers": [
            "C000F001B0002",
            "C000F001B0003",
            "C000F001B0005",
            "C000F001B0007",
        ],
    },
]

SELECT_REPOSITORY_CASES_ERROR = [
    {
        "id": "unknown_repo_id",
        "repo_id": "missing",
        "default_repo_id": "default",
        "merged": {"default": "factory_default"},
        "builtins": {"default"},
        "expect_substrings": [
            "unknown repository id",
            "'missing'",
            "available=",
        ],
        "covers": [
            "C000F001B0001",
            "C000F001B0003",
            "C000F001B0004",
        ],
    },
]

OPEN_REPOSITORY_CASES = [
    {
        "id": "registry_none_builds_and_closes_on_normal_exit",
        "pass_registry": None,
        "repo_id": "r1",
        "config": {"k": "v"},
        "merged": {"r1": "factory_r1"},
        "builtins": {"r1"},
        "factory_raises": None,
        "block_raises": None,
        "expect_build_registry_called": True,
        "expect_close_called": True,
        "covers": [
            "C000F002B0001",
            "C000F002B0003",
            "C000F002B0006",
            "C000F002B0008",
        ],
    },
    {
        "id": "registry_provided_does_not_build",
        "pass_registry": "provided",
        "repo_id": "r1",
        "config": None,
        "merged": {"r1": "factory_r1"},
        "builtins": {"r1"},
        "factory_raises": None,
        "block_raises": None,
        "expect_build_registry_called": False,
        "expect_close_called": True,
        "covers": [
            "C000F002B0002",
            "C000F002B0003",
            "C000F002B0006",
            "C000F002B0008",
        ],
    },
    {
        "id": "registry_error_wrapped",
        "pass_registry": "provided",
        "repo_id": "r1",
        "config": None,
        "merged": "RAISE_REGISTRY_ERROR",
        "builtins": set(),
        "factory_raises": None,
        "block_raises": None,
        "expect_build_registry_called": False,
        "expect_close_called": False,
        "expect_exception": factory.RepositorySelectionError,
        "expect_substrings": ["registry boom"],
        "covers": [
            "C000F002B0002",
            "C000F002B0004",
        ],
    },
    {
        "id": "selection_error_propagates",
        "pass_registry": "provided",
        "repo_id": "missing",
        "config": None,
        "merged": {"r1": "factory_r1"},
        "builtins": set(),
        "factory_raises": None,
        "block_raises": None,
        "expect_build_registry_called": False,
        "expect_close_called": False,
        "expect_exception": factory.RepositorySelectionError,
        "expect_substrings": ["unknown repository id", "'missing'"],
        "covers": [
            "C000F002B0002",
            "C000F002B0005",
        ],
    },
    {
        "id": "factory_raises_propagates_and_no_close",
        "pass_registry": "provided",
        "repo_id": "r1",
        "config": None,
        "merged": {"r1": "factory_r1"},
        "builtins": {"r1"},
        "factory_raises": RuntimeError("factory boom"),
        "block_raises": None,
        "expect_build_registry_called": False,
        "expect_close_called": False,
        "expect_exception": RuntimeError,
        "expect_substrings": ["factory boom"],
        "covers": [
            "C000F002B0002",
            "C000F002B0003",
            "C000F002B0007",
        ],
    },
    {
        "id": "block_raises_still_closes_and_propagates",
        "pass_registry": "provided",
        "repo_id": "r1",
        "config": None,
        "merged": {"r1": "factory_r1"},
        "builtins": {"r1"},
        "factory_raises": None,
        "block_raises": ValueError("block boom"),
        "expect_build_registry_called": False,
        "expect_close_called": True,
        "expect_exception": ValueError,
        "expect_substrings": ["block boom"],
        "covers": [
            "C000F002B0002",
            "C000F002B0003",
            "C000F002B0006",
            "C000F002B0009",
        ],
    },
]


# ==============================================================================
# TESTS
# ==============================================================================


@pytest.mark.parametrize("case", SELECT_REPOSITORY_CASES_SUCCESS, ids=lambda c: c["id"])
def test_select_repository_success(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Covers: see case["covers"]
    merged_called = Mock(name="merged_called")

    def _merged_impl() -> dict[str, Any]:
        merged_called()
        return dict(case["merged"])

    registry = _RegistryStub(merged_impl=_merged_impl, builtins=set(case["builtins"]))
    monkeypatch.setattr(factory, "DEFAULT_REPOSITORY_ID", case["default_repo_id"])

    selection = factory._select_repository(
        repo_id=case["repo_id"], registry=registry
    )  # noqa: SLF001

    merged_called.assert_called_once_with()  # C000F001B0003
    assert selection.repo_id == case["expect_repo_id"]
    assert selection.origin == case["expect_origin"]
    assert selection.factory == case["expect_factory"]


@pytest.mark.parametrize("case", SELECT_REPOSITORY_CASES_ERROR, ids=lambda c: c["id"])
def test_select_repository_unknown_repo_raises(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Covers: see case["covers"]
    merged_called = Mock(name="merged_called")

    def _merged_impl() -> dict[str, Any]:
        merged_called()
        return dict(case["merged"])

    registry = _RegistryStub(merged_impl=_merged_impl, builtins=set(case["builtins"]))
    monkeypatch.setattr(factory, "DEFAULT_REPOSITORY_ID", case["default_repo_id"])

    with pytest.raises(factory.RepositorySelectionError) as excinfo:
        factory._select_repository(
            repo_id=case["repo_id"], registry=registry
        )  # noqa: SLF001

    merged_called.assert_called_once_with()  # C000F001B0003
    msg = str(excinfo.value)
    for s in case["expect_substrings"]:
        assert s in msg


@pytest.mark.parametrize("case", OPEN_REPOSITORY_CASES, ids=lambda c: c["id"])
def test_open_repository(case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: see case["covers"]
    build_registry_mock = Mock(name="build_repository_registry")

    # Patch RepositoryRegistryError so open_repository catches a deterministic type.
    class _RegistryError(Exception):
        pass

    monkeypatch.setattr(factory, "RepositoryRegistryError", _RegistryError)

    close_mock = Mock(name="repo_close")
    repo = _RepoStub(close_mock=close_mock)

    factory_callable = Mock(name="repo_factory")
    if case["factory_raises"] is None:
        factory_callable.return_value = repo
    else:
        factory_callable.side_effect = case["factory_raises"]

    if case["merged"] == "RAISE_REGISTRY_ERROR":
        registry = _RegistryStub(
            merged_impl=Mock(side_effect=_RegistryError("registry boom")),
            builtins=set(case["builtins"]),
        )
    else:
        merged_map = dict(case["merged"])  # type: ignore[arg-type]
        # Replace the repo factory marker with the callable that returns our repo.
        merged_map = {
            k: (factory_callable if v == "factory_r1" else v)
            for k, v in merged_map.items()
        }
        registry = _RegistryStub(
            merged_impl=Mock(return_value=merged_map), builtins=set(case["builtins"])
        )

    build_registry_mock.return_value = registry
    monkeypatch.setattr(factory, "build_repository_registry", build_registry_mock)

    provided_registry = None if case["pass_registry"] is None else registry

    def _use_repo() -> None:
        with factory.open_repository(
            repo_id=case["repo_id"],
            config=case["config"],
            registry=provided_registry,
        ) as opened:
            # C000F002B0006: yielded object is the repo instance produced by the factory.
            assert opened is repo

            if case["block_raises"] is not None:
                raise case["block_raises"]

    if "expect_exception" in case:
        with pytest.raises(case["expect_exception"]) as excinfo:
            _use_repo()
        for s in case.get("expect_substrings", []):
            assert s in str(excinfo.value)
    else:
        _use_repo()

    if case["expect_build_registry_called"]:
        build_registry_mock.assert_called_once_with()
    else:
        build_registry_mock.assert_not_called()

    if case["expect_close_called"]:
        close_mock.assert_called_once_with()
    else:
        close_mock.assert_not_called()

    # If we reached repo construction, ensure config was forwarded as keyword arg.
    if (
        case.get("merged") not in ("RAISE_REGISTRY_ERROR",)
        and case.get("expect_exception") is not factory.RepositorySelectionError
    ):
        if case["repo_id"] == "r1":
            # C000F002B0006 / C000F002B0007 (factory invocation path)
            factory_callable.assert_called_once_with(config=case["config"])
