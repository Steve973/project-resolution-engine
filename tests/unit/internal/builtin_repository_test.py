from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from project_resolution_engine.internal import builtin_repository as uut
from unit.helpers.models_helper import (
    FakeArtifactRecord,
    FakeCoreMetadataKey,
    FakeIndexMetadataKey,
    FakeWheelKey,
)

# ==============================================================================
# BRANCH LEDGER: builtin_repository (C000)
# ==============================================================================
#
# Classes:
#   - EphemeralArtifactRepository (C001)
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.__init__(self, *, prefix: str = "project-resolution-engine-ephemeral-")
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: (linear execution) -> initializes _tmp, _root, and _index (empty dict)
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.root_path(self)
#    (Class ID: C001, Method ID: M002)
# ------------------------------------------------------------------------------
# C001M002B0001: (linear execution) -> returns self._root
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.root_uri(self)
#    (Class ID: C001, Method ID: M003)
# ------------------------------------------------------------------------------
# C001M003B0001: (linear execution) -> returns self._root.as_uri()
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.close(self)
#    (Class ID: C001, Method ID: M004)
# ------------------------------------------------------------------------------
# C001M004B0001: (linear execution) -> clears self._index and calls self._tmp.cleanup()
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.__enter__(self)
#    (Class ID: C001, Method ID: M005)
# ------------------------------------------------------------------------------
# C001M005B0001: (linear execution) -> returns self
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.__exit__(self, exc_type, exc, tb)
#    (Class ID: C001, Method ID: M006)
# ------------------------------------------------------------------------------
# C001M006B0001: (linear execution) -> calls self.close() and returns None
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.get(self, key: BaseArtifactKey)
#    (Class ID: C001, Method ID: M007)
# ------------------------------------------------------------------------------
# C001M007B0001: record is None -> returns None
# C001M007B0002: record is not None -> continues with dest = record.destination_uri
# C001M007B0003: dest.startswith("file://") is False -> returns record
# C001M007B0004: dest.startswith("file://") is True -> enters try block to validate underlying file exists
# C001M007B0005: not path.exists() -> self._index.pop(key, None) and returns None
# C001M007B0006: path.exists() -> returns record
# C001M007B0007: except Exception: -> returns record
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.put(self, record: ArtifactRecord)
#    (Class ID: C001, Method ID: M008)
# ------------------------------------------------------------------------------
# C001M008B0001: (linear execution) -> stores record in self._index under record.key
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.delete(self, key: BaseArtifactKey)
#    (Class ID: C001, Method ID: M009)
# ------------------------------------------------------------------------------
# C001M009B0001: record is None -> returns (no deletion)
# C001M009B0002: record is not None -> continues with dest = record.destination_uri
# C001M009B0003: not dest.startswith("file://") -> returns (no file deletion attempted)
# C001M009B0004: dest.startswith("file://") -> enters try block to best-effort delete file
# C001M009B0005: self._is_under_root(path) and path.exists() -> calls path.unlink()
# C001M009B0006: not (self._is_under_root(path) and path.exists()) -> does nothing and returns None
# C001M009B0007: except Exception: -> returns (swallows cleanup error)
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository.allocate_destination_uri(self, key: BaseArtifactKey)
#    (Class ID: C001, Method ID: M010)
# ------------------------------------------------------------------------------
# C001M010B0001: (linear execution) -> allocates path via self._allocate_path_for_key(key), mkdirs parent, returns path.as_uri()
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository._is_under_root(self, path: Path)
#    (Class ID: C001, Method ID: M011)
# ------------------------------------------------------------------------------
# C001M011B0001: try: path.relative_to(self._root) succeeds -> returns True
# C001M011B0002: except Exception: -> returns False
#
# ------------------------------------------------------------------------------
# ## EphemeralArtifactRepository._allocate_path_for_key(self, key: BaseArtifactKey)
#    (Class ID: C001, Method ID: M012)
# ------------------------------------------------------------------------------
# C001M012B0001: case IndexMetadataKey() as k: -> returns self._root / "index_metadata" / _short_hash(k.index_base) / f"{_safe_segment(k.project)}.json"
# C001M012B0002: case CoreMetadataKey() as k: -> returns self._root / "core_metadata" / _safe_segment(k.name) / _safe_segment(k.version) / _safe_segment(k.tag) / f"{_short_hash(k.file_url)}.metadata"
# C001M012B0003: case WheelKey() as k: -> enters WheelKey allocation flow
# C001M012B0004: if k.origin_uri is None: -> raises ValueError (message contains "WheelKey must have an origin_uri")
# C001M012B0005: if k.origin_uri is not None: -> continues with url_hash = _short_hash(k.origin_uri) and base = _url_basename(k.origin_uri)
# C001M012B0006: if base is not None and base.endswith(".whl"): -> filename = f"{url_hash}-{_safe_segment(base)}"
# C001M012B0007: else: -> filename = f"{url_hash}.whl"
# C001M012B0008: (WheelKey path return) -> returns self._root / "wheels" / _safe_segment(k.name) / _safe_segment(k.version) / _safe_segment(k.tag) / filename
# C001M012B0009: case _: -> raises TypeError (message contains "Unsupported artifact key type:")
#

# ==============================================================================
# Case matrices (per TESTING_CONTRACT.md)
# ==============================================================================

GET_CASES: list[dict[str, Any]] = [
    {
        "name": "miss_returns_none",
        "dest_uri": None,
        "path_exists": None,
        "force_path_exception": False,
        "expect": None,
        "expect_index_retains_key": False,
        "covers": ["C001M007B0001"],
    },
    {
        "name": "hit_non_file_dest_returns_record",
        "dest_uri": "mem://artifact/wheel/abc123",
        "path_exists": None,
        "force_path_exception": False,
        "expect": "record",
        "expect_index_retains_key": True,
        "covers": ["C001M007B0002", "C001M007B0003"],
    },
    {
        "name": "hit_file_dest_missing_file_drops_index_and_returns_none",
        "dest_uri": "file://{path}",
        "path_exists": False,
        "force_path_exception": False,
        "expect": None,
        "expect_index_retains_key": False,
        "covers": ["C001M007B0002", "C001M007B0004", "C001M007B0005"],
    },
    {
        "name": "hit_file_dest_existing_file_returns_record",
        "dest_uri": "file://{path}",
        "path_exists": True,
        "force_path_exception": False,
        "expect": "record",
        "expect_index_retains_key": True,
        "covers": ["C001M007B0002", "C001M007B0004", "C001M007B0006"],
    },
    {
        "name": "hit_file_dest_path_parse_exception_returns_record",
        "dest_uri": "file://this-will-trigger-path-construction",
        "path_exists": None,
        "force_path_exception": True,
        "expect": "record",
        "expect_index_retains_key": True,
        "covers": ["C001M007B0002", "C001M007B0004", "C001M007B0007"],
    },
]

DELETE_CASES: list[dict[str, Any]] = [
    {
        "name": "delete_miss_returns",
        "dest_uri": None,
        "create_file": False,
        "expect_file_deleted": False,
        "force_path_exception": False,
        "covers": ["C001M009B0001"],
    },
    {
        "name": "delete_hit_non_file_dest_no_file_delete_attempted",
        "dest_uri": "mem://artifact/wheel/abc123",
        "create_file": False,
        "expect_file_deleted": False,
        "force_path_exception": False,
        "covers": ["C001M009B0002", "C001M009B0003"],
    },
    {
        "name": "delete_hit_file_dest_under_root_and_exists_unlinks",
        "dest_uri": "file://{path}",
        "create_file": True,
        "expect_file_deleted": True,
        "force_path_exception": False,
        "covers": ["C001M009B0002", "C001M009B0004", "C001M009B0005"],
    },
    {
        "name": "delete_hit_file_dest_under_root_missing_file_no_unlink",
        "dest_uri": "file://{path}",
        "create_file": False,
        "expect_file_deleted": False,
        "force_path_exception": False,
        "covers": ["C001M009B0002", "C001M009B0004", "C001M009B0006"],
    },
    {
        "name": "delete_hit_file_dest_path_exception_swallowed",
        "dest_uri": "file://this-will-trigger-path-construction",
        "create_file": False,
        "expect_file_deleted": False,
        "force_path_exception": True,
        "covers": ["C001M009B0002", "C001M009B0004", "C001M009B0007"],
    },
]

ALLOCATE_PATH_CASES: list[dict[str, Any]] = [
    {
        "name": "index_metadata_key_path",
        "key_factory": lambda: FakeIndexMetadataKey(project="Requests"),
        "expect_exception": None,
        "assertions": "index_metadata",
        "covers": ["C001M012B0001"],
    },
    {
        "name": "core_metadata_key_path",
        "key_factory": lambda: FakeCoreMetadataKey(
            name="requests",
            version="2.0",
            tag="py3-none-any",
            file_url="https://example.com/files/requests-2.0.whl",
        ),
        "expect_exception": None,
        "assertions": "core_metadata",
        "covers": ["C001M012B0002"],
    },
    {
        "name": "wheel_key_missing_origin_raises",
        "key_factory": lambda: FakeWheelKey(
            name="requests", version="2.0", tag="py3-none-any", origin_uri=None
        ),
        "expect_exception": (ValueError, "WheelKey must have an origin_uri"),
        "assertions": None,
        "covers": ["C001M012B0003", "C001M012B0004"],
    },
    {
        "name": "wheel_key_with_whl_basename_uses_hash_and_sanitized_basename",
        "key_factory": lambda: FakeWheelKey(
            name="requests",
            version="2.0",
            tag="py3-none-any",
            origin_uri="https://example.com/packages/Req uests-2.0-py3-none-any.whl",
        ),
        "expect_exception": None,
        "assertions": "wheel_basename_whl",
        "covers": ["C001M012B0003", "C001M012B0005", "C001M012B0006", "C001M012B0008"],
    },
    {
        "name": "wheel_key_without_whl_basename_uses_hash_only",
        "key_factory": lambda: FakeWheelKey(
            name="requests",
            version="2.0",
            tag="py3-none-any",
            origin_uri="https://example.com/download",
        ),
        "expect_exception": None,
        "assertions": "wheel_basename_else",
        "covers": ["C001M012B0003", "C001M012B0005", "C001M012B0007", "C001M012B0008"],
    },
    {
        "name": "unsupported_key_type_raises_typeerror",
        "key_factory": lambda: object(),
        "expect_exception": (TypeError, "Unsupported artifact key type:"),
        "assertions": None,
        "covers": ["C001M012B0009"],
    },
]

# ==============================================================================
# Helpers / fakes
# ==============================================================================


@dataclass(slots=True)
class _FakeTemporaryDirectory:
    """
    Deterministic stand-in for tempfile.TemporaryDirectory, rooted under tmp_path.
    """

    name: str
    cleanup_calls: int = 0

    def cleanup(self) -> None:
        self.cleanup_calls += 1


def _install_fake_tempdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> _FakeTemporaryDirectory:
    root = tmp_path / "ephemeral-root"
    root.mkdir(parents=True, exist_ok=True)
    fake = _FakeTemporaryDirectory(name=str(root))

    def _factory(
        *, prefix: str = "ignored"
    ) -> _FakeTemporaryDirectory:  # matches uut call signature
        return fake

    monkeypatch.setattr(uut.tempfile, "TemporaryDirectory", _factory)
    return fake


def _patch_key_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure structural pattern matches in _allocate_path_for_key see our fakes.
    """
    monkeypatch.setattr(uut, "IndexMetadataKey", FakeIndexMetadataKey)
    monkeypatch.setattr(uut, "CoreMetadataKey", FakeCoreMetadataKey)
    monkeypatch.setattr(uut, "WheelKey", FakeWheelKey)


def _mk_record(
    *, key: Any, destination_uri: str, origin_uri: str = "mem://origin"
) -> FakeArtifactRecord:
    return FakeArtifactRecord(
        key=key, destination_uri=destination_uri, origin_uri=origin_uri
    )


# ==============================================================================
# Tests
# ==============================================================================


def test_init_sets_root_and_empty_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M001B0001
    fake_tmp = _install_fake_tempdir(monkeypatch, tmp_path)

    repo = uut.EphemeralArtifactRepository(prefix="x-")

    assert repo._tmp is fake_tmp
    assert repo.root_path == Path(fake_tmp.name).resolve()
    assert repo._index == {}


def test_root_path_and_root_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M002B0001, C001M003B0001
    fake_tmp = _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()

    assert repo.root_path == Path(fake_tmp.name).resolve()
    assert repo.root_uri == Path(fake_tmp.name).resolve().as_uri()


# noinspection PyTypeChecker
def test_close_clears_index_and_cleans_tempdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M004B0001
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()
    repo._index["k"] = "v"

    repo.close()

    assert repo._index == {}
    assert repo._tmp.cleanup_calls == 1


# noinspection PyTypeChecker
def test_enter_returns_self_and_exit_calls_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M005B0001, C001M006B0001 (and close side-effects)
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()
    repo._index["k"] = "v"

    entered = repo.__enter__()
    assert entered is repo

    repo.__exit__(None, None, None)
    assert repo._index == {}
    assert repo._tmp.cleanup_calls == 1


# noinspection PyTypeChecker
@pytest.mark.parametrize("case", GET_CASES, ids=[c["name"] for c in GET_CASES])
def test_get_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # covers: see case["covers"]
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()

    key = FakeIndexMetadataKey(project="requests")

    if case["dest_uri"] is None:
        assert repo.get(key) is None
        return

    dest_uri = case["dest_uri"]
    if "{path}" in dest_uri:
        p = repo.root_path / "some" / "file.bin"
        if case["path_exists"]:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        dest_uri = dest_uri.format(path=p.as_posix())

    record = _mk_record(key=key, destination_uri=dest_uri)
    repo.put(record)

    if case["force_path_exception"]:

        def _boom_path(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(uut, "Path", _boom_path)

    got = repo.get(key)
    if case["expect"] is None:
        assert got is None
    else:
        assert got is record

    assert (key in repo._index) is case["expect_index_retains_key"]


# noinspection PyTypeChecker
def test_put_stores_record_by_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M008B0001
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()

    key = FakeIndexMetadataKey(project="requests")
    record = _mk_record(key=key, destination_uri="mem://artifact/x")

    repo.put(record)

    assert repo._index[key] is record


# noinspection PyTypeChecker
@pytest.mark.parametrize("case", DELETE_CASES, ids=[c["name"] for c in DELETE_CASES])
def test_delete_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # covers: see case["covers"]
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()

    key = FakeIndexMetadataKey(project="requests")

    if case["dest_uri"] is None:
        repo.delete(key)
        assert repo.get(key) is None
        return

    dest_uri = case["dest_uri"]
    file_path: Path | None = None
    if "{path}" in dest_uri:
        file_path = repo.root_path / "some" / "victim.bin"
        dest_uri = dest_uri.format(path=file_path.as_posix())
        if case["create_file"]:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"x")

    record = _mk_record(key=key, destination_uri=dest_uri)
    repo.put(record)

    if case["force_path_exception"]:

        def _boom_path(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(uut, "Path", _boom_path)

    repo.delete(key)
    assert key not in repo._index

    if file_path is not None:
        if case["expect_file_deleted"]:
            assert not file_path.exists()
        else:
            if case["create_file"]:
                assert file_path.exists()


# noinspection PyTypeChecker
def test_allocate_destination_uri_mkdirs_parent_and_returns_file_uri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # covers: C001M010B0001
    _install_fake_tempdir(monkeypatch, tmp_path)
    _patch_key_types(monkeypatch)
    repo = uut.EphemeralArtifactRepository()

    key = FakeIndexMetadataKey(project="requests", index_base="https://pypi.org/simple")
    uri = repo.allocate_destination_uri(key)

    assert uri.startswith("file://")
    p = Path(uri.removeprefix("file://"))
    assert p.parent.exists()


@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "under_root_true",
            "rel": Path("a/b/c.txt"),
            "expect": True,
            "covers": ["C001M011B0001"],
        },
        {
            "name": "under_root_false",
            "rel": None,
            "expect": False,
            "covers": ["C001M011B0002"],
        },
    ],
    ids=lambda c: c["name"],
)
def test_is_under_root_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # covers: see case["covers"]
    _install_fake_tempdir(monkeypatch, tmp_path)
    repo = uut.EphemeralArtifactRepository()

    if case["rel"] is None:
        outside = tmp_path / "outside.txt"
        assert repo._is_under_root(outside) is False
    else:
        inside = repo.root_path / case["rel"]
        assert repo._is_under_root(inside) is True


@pytest.mark.parametrize(
    "case", ALLOCATE_PATH_CASES, ids=[c["name"] for c in ALLOCATE_PATH_CASES]
)
def test_allocate_path_for_key_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]
) -> None:
    # covers: see case["covers"]
    _install_fake_tempdir(monkeypatch, tmp_path)
    _patch_key_types(monkeypatch)
    repo = uut.EphemeralArtifactRepository()

    key = case["key_factory"]()
    exc_spec = case["expect_exception"]
    if exc_spec is not None:
        exc_type, msg_sub = exc_spec
        with pytest.raises(exc_type, match=re.escape(msg_sub) if msg_sub else None):
            repo._allocate_path_for_key(key)  # type: ignore[arg-type]
        return

    path = repo._allocate_path_for_key(key)  # type: ignore[arg-type]
    assert path.is_absolute()
    assert str(path).startswith(str(repo.root_path))

    if case["assertions"] == "index_metadata":
        assert path.parts[-3] == "index_metadata"
        assert path.name.endswith(".json")

    elif case["assertions"] == "core_metadata":
        assert "core_metadata" in path.parts
        assert path.name.endswith(".metadata")

    elif case["assertions"] == "wheel_basename_whl":
        assert "wheels" in path.parts
        filename = path.name
        assert filename.endswith(".whl")

        expected_hash = uut._short_hash(key.origin_uri)  # type: ignore[arg-type]
        base = uut._url_basename(key.origin_uri)  # type: ignore[arg-type]
        assert base is not None and base.endswith(".whl")

        assert filename.startswith(expected_hash + "-")
        assert uut._safe_segment(base) in filename

    elif case["assertions"] == "wheel_basename_else":
        assert "wheels" in path.parts
        expected_hash = uut._short_hash(key.origin_uri)  # type: ignore[arg-type]
        assert path.name == f"{expected_hash}.whl"
