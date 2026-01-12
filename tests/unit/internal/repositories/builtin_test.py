from __future__ import annotations

import builtins
import sys
import types
from typing import Any

import pytest

import project_resolution_engine.internal.repositories.builtin as uut

# ==============================================================================
# 7) CASE MATRIX (covers new branches only)
# ==============================================================================

_CREATE_EPHEMERAL_SUCCESS_CASES: list[dict[str, Any]] = [
    {
        "case_id": "config_none",
        "config": None,
        "covers": ["C000F001B0001"],
    },
    {
        "case_id": "config_mapping_ignored",
        "config": {"any": "value"},
        "covers": ["C000F001B0001"],
    },
]

_CREATE_EPHEMERAL_IMPORT_FAIL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "import_error_forced",
        "covers": ["C000F001B0002"],
    },
]


# ==============================================================================
# 8) TESTS
# ==============================================================================

@pytest.mark.parametrize(
    "case",
    _CREATE_EPHEMERAL_SUCCESS_CASES,
    ids=lambda c: c["case_id"],
)
def test__create_ephemeral_import_succeeds_returns_instance(case: dict[str, Any],
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: C000F001B0001
    #
    # External influence mocked:
    # - import of project_resolution_engine.internal.builtin_repository is satisfied via sys.modules injection

    class FakeEphemeralArtifactRepository:
        def __init__(self) -> None:
            self.created = True

    fake_mod = types.ModuleType("project_resolution_engine.internal.builtin_repository")
    fake_mod.EphemeralArtifactRepository = FakeEphemeralArtifactRepository  # type: ignore[attr-defined]

    # Ensure import resolution uses our fake module.
    monkeypatch.setitem(sys.modules, "project_resolution_engine.internal.builtin_repository", fake_mod)

    repo = uut._create_ephemeral(config=case["config"])

    assert isinstance(repo, FakeEphemeralArtifactRepository)
    assert getattr(repo, "created", False) is True


@pytest.mark.parametrize(
    "case",
    _CREATE_EPHEMERAL_IMPORT_FAIL_CASES,
    ids=lambda c: c["case_id"],
)
def test__create_ephemeral_import_fails_raises_import_error(case: dict[str, Any],
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: C000F001B0002
    #
    # External influence mocked:
    # - import machinery at the call site (the local import inside uut._create_ephemeral)

    original_import = builtins.__import__

    def _import_hook(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
        if name == "project_resolution_engine.internal.builtin_repository":
            raise ImportError("forced import failure for test coverage")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _import_hook)

    with pytest.raises(ImportError) as excinfo:
        uut._create_ephemeral(config=None)

    assert "forced import failure" in str(excinfo.value)


def test_defaults_and_factory_registry_are_wired_correctly() -> None:
    # No new branches (constants / mapping), but asserts the module contract.
    assert uut.DEFAULT_REPOSITORY_ID == "ephemeral"
    assert "ephemeral" in uut.BUILTIN_REPOSITORY_FACTORIES
    assert uut.BUILTIN_REPOSITORY_FACTORIES["ephemeral"] is uut._create_ephemeral
    assert callable(uut.BUILTIN_REPOSITORY_FACTORIES["ephemeral"])
