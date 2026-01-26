from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pytest

import project_resolution_engine.internal.builtin_strategies as mod

# ==============================================================================
# BRANCH LEDGER: builtin_strategies (C000)
# ==============================================================================
#
# ------------------------------------------------------------------------------
# ## _safe_segment(value: str) -> str
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: if not value -> returns "_" (after strip yields empty)
# C000F001B0002: else (value truthy after strip) -> returns _INVALID_SEGMENT_CHARS.sub("_", value) truncated to 160 chars
#
# ------------------------------------------------------------------------------
# ## _short_hash(value: str) -> str
#    (Module ID: C000, Function ID: F002)
# ------------------------------------------------------------------------------
# C000F002B0001: unconditionally -> returns hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
#
# ------------------------------------------------------------------------------
# ## _url_basename(url: str) -> str | None
#    (Module ID: C000, Function ID: F003)
# ------------------------------------------------------------------------------
# C000F003B0001: try: if not parsed.path -> returns None
# C000F003B0002: try: else (parsed.path truthy) and base = Path(unquote(parsed.path)).name is truthy -> returns base
# C000F003B0003: try: else (parsed.path truthy) and base = Path(unquote(parsed.path)).name is falsy -> returns None
# C000F003B0004: except Exception -> returns None
#
# ------------------------------------------------------------------------------
# ## _require_file_destination(destination_uri: str) -> Path
#    (Module ID: C000, Function ID: F004)
# ------------------------------------------------------------------------------
# C000F004B0001: if parsed.scheme != "file" -> raises ValueError("Built-in strategies require file:// destination URIs, got: ...")
# C000F004B0002: else (parsed.scheme == "file") -> returns Path(parsed.path)
#
# ------------------------------------------------------------------------------
# ## _ensure_parent_dir(path: Path) -> None
#    (Module ID: C000, Function ID: F005)
# ------------------------------------------------------------------------------
# C000F005B0001: unconditionally -> calls path.parent.mkdir(parents=True, exist_ok=True)
#
# ------------------------------------------------------------------------------
# ## _sha256_file(path: Path) -> str
#    (Module ID: C000, Function ID: F006)
# ------------------------------------------------------------------------------
# C000F006B0001: for chunk in iter(lambda: f.read(1024 * 1024), b""): loop executes 0 times -> returns sha256 of empty content (hexdigest)
# C000F006B0002: for chunk in iter(lambda: f.read(1024 * 1024), b""): loop executes >= 1 time -> returns sha256 of file bytes (hexdigest)
#
# ------------------------------------------------------------------------------
# ## _simple_project_json_url(index_base: str, project: str) -> str
#    (Module ID: C000, Function ID: F007)
# ------------------------------------------------------------------------------
# C000F007B0001: unconditionally -> returns f"{index_base.rstrip('/') + '/'}{project.strip('/')}/"
#
# ------------------------------------------------------------------------------
# ## _write_canonical_json(path: Path, payload: Any) -> None
#    (Module ID: C000, Function ID: F008)
# ------------------------------------------------------------------------------
# C000F008B0001: unconditionally -> writes json.dumps(payload, indent=2, sort_keys=True) + "\n" to path (utf-8)
#
# ------------------------------------------------------------------------------
# ## _pep658_metadata_url(file_url: str) -> str
#    (Module ID: C000, Function ID: F009)
# ------------------------------------------------------------------------------
# C000F009B0001: unconditionally -> returns f"{file_url}.metadata"
#
# ------------------------------------------------------------------------------
# ## _find_dist_info_metadata_path(zf: zipfile.ZipFile) -> str
#    (Module ID: C000, Function ID: F010)
# ------------------------------------------------------------------------------
# C000F010B0001: if not candidates -> raises FileNotFoundError("Wheel does not contain any *.dist-info/METADATA entry")
# C000F010B0002: else (candidates truthy) -> returns sorted(candidates)[0]
#
# ------------------------------------------------------------------------------
# ## Pep691IndexMetadataHttpStrategy.resolve(self, *, key: IndexMetadataKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C001, Method ID: M001)
# ------------------------------------------------------------------------------
# C001M001B0001: if not isinstance(key, IndexMetadataKey) -> raises StrategyNotApplicable()
# C001M001B0002: else (isinstance(key, IndexMetadataKey)) -> downloads PEP 691 JSON, writes canonical JSON to dest_path, returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# ## HttpWheelFileStrategy.resolve(self, *, key: WheelKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C002, Method ID: M001)
# ------------------------------------------------------------------------------
# C002M001B0001: if not isinstance(key, WheelKey) -> raises StrategyNotApplicable()
# C002M001B0002: else (isinstance(key, WheelKey)) and if key.origin_uri is None -> raises ValueError("WheelKey must have origin_uri set")
# C002M001B0003: else (isinstance(key, WheelKey)) and else (key.origin_uri is not None) and for chunk in resp.iter_content(...): loop executes 0 times -> writes no bytes; returns ArtifactRecord for (possibly empty) dest_path
# C002M001B0004: else (isinstance(key, WheelKey)) and else (key.origin_uri is not None) and for chunk ...: loop executes >= 1 time and if chunk -> writes chunk bytes; returns ArtifactRecord
# C002M001B0005: else (isinstance(key, WheelKey)) and else (key.origin_uri is not None) and for chunk ...: loop executes >= 1 time and else (not chunk) -> skips write for that iteration; returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# ## Pep658CoreMetadataHttpStrategy.resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C003, Method ID: M001)
# ------------------------------------------------------------------------------
# C003M001B0001: if not isinstance(key, CoreMetadataKey) -> raises StrategyNotApplicable()
# C003M001B0002: else (isinstance(key, CoreMetadataKey)) and if resp.status_code == 404 -> raises StrategyNotApplicable()
# C003M001B0003: else (isinstance(key, CoreMetadataKey)) and else (resp.status_code != 404) -> writes resp.content to dest_path; returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# ## WheelExtractedCoreMetadataStrategy.resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C004, Method ID: M001)
# ------------------------------------------------------------------------------
# C004M001B0001: if not isinstance(key, CoreMetadataKey) -> raises StrategyNotApplicable()
# C004M001B0002: else (isinstance(key, CoreMetadataKey)) -> downloads wheel via injected wheel_strategy, extracts *.dist-info/METADATA, writes to dest_path, returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# ## DirectUriWheelFileStrategy.resolve(self, *, key: WheelKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C005, Method ID: M001)
# ------------------------------------------------------------------------------
# C005M001B0001: if not isinstance(key, WheelKey) -> raises StrategyNotApplicable()
# C005M001B0002: else (isinstance(key, WheelKey)) and if key.origin_uri is None -> raises ValueError("WheelKey must have origin_uri set")
# C005M001B0003: else (isinstance(key, WheelKey)) and else (key.origin_uri is not None) and if src_parsed.scheme not in ("file", "") -> raises StrategyNotApplicable()
# C005M001B0004: else (...) and else (src_parsed.scheme in ("file", "")) and if not src_path.exists() -> raises FileNotFoundError(str(src_path))
# C005M001B0005: else (...) and else (src_path.exists()) and for chunk in iter(lambda: r.read(self.chunk_bytes), b""): loop executes 0 times -> writes no bytes; returns ArtifactRecord for (possibly empty) dest_path
# C005M001B0006: else (...) and else (src_path.exists()) and for chunk ...: loop executes >= 1 time -> copies bytes; returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# ## DirectUriCoreMetadataStrategy.resolve(self, *, key: CoreMetadataKey, destination_uri: str) -> ArtifactRecord | None
#    (Class ID: C006, Method ID: M001)
# ------------------------------------------------------------------------------
# C006M001B0001: if not isinstance(key, CoreMetadataKey) -> raises StrategyNotApplicable()
# C006M001B0002: else (isinstance(key, CoreMetadataKey)) and if parsed.scheme not in ("", "file") -> raises StrategyNotApplicable()
# C006M001B0003: else (...) and else (parsed.scheme in ("", "file")) and if not wheel_path.exists() -> raises FileNotFoundError(str(wheel_path))
# C006M001B0004: else (...) and else (wheel_path.exists()) and if not wheel_path.is_file() -> raises ValueError(f"Core metadata file_url is not a file: {wheel_path}")
# C006M001B0005: else (...) and else (wheel_path.exists() and wheel_path.is_file()) -> extracts *.dist-info/METADATA from wheel_path into dest_path; returns ArtifactRecord
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none in this module)
#   [x] all `except` handlers captured
#   [x] all early `return`s / `raise`s / `yield`s captured
#   [x] all loop 0 vs >= 1 iterations captured
#   [x] all `break` / `continue` paths captured (none in this module)
# ==============================================================================


# ==============================================================================
# Case matrices (contract §7)
# ==============================================================================

SAFE_SEGMENT_CASES = [
    # covers: C000F001B0001
    ("   ", "_", ["C000F001B0001"]),
    # covers: C000F001B0002
    (" a b*c ", "a_b_c", ["C000F001B0002"]),
    # covers: C000F001B0002 (truncate)
    ("x" * 999, "x" * 160, ["C000F001B0002"]),
]

URL_BASENAME_CASES = [
    # covers: C000F003B0001
    ("https://example.com", None, ["C000F003B0001"]),
    # covers: C000F003B0002
    ("https://example.com/files/pkg-1.0.whl", "pkg-1.0.whl", ["C000F003B0002"]),
    # covers: C000F003B0003 (path is "/" -> Path("/").name == "")
    ("https://example.com/", None, ["C000F003B0003"]),
]

REQUIRE_FILE_DESTINATION_CASES = [
    # covers: C000F004B0001
    ("s3://bucket/key", ValueError, "require file://", ["C000F004B0001"]),
    # covers: C000F004B0002
    ("file:///tmp/somewhere.txt", Path("/tmp/somewhere.txt"), None, ["C000F004B0002"]),
]

SHA256_FILE_CASES = [
    # covers: C000F006B0001
    (b"", hashlib.sha256(b"").hexdigest(), ["C000F006B0001"]),
    # covers: C000F006B0002
    (b"abc", hashlib.sha256(b"abc").hexdigest(), ["C000F006B0002"]),
]

SIMPLE_PROJECT_JSON_URL_CASES = [
    # covers: C000F007B0001
    (
        "https://pypi.org/simple",
        "requests",
        "https://pypi.org/simple/requests/",
        ["C000F007B0001"],
    ),
    (
        "https://pypi.org/simple/",
        "/requests/",
        "https://pypi.org/simple/requests/",
        ["C000F007B0001"],
    ),
]

PEP658_URL_CASES = [
    # covers: C000F009B0001
    (
        "https://files.pythonhosted.org/x.whl",
        "https://files.pythonhosted.org/x.whl.metadata",
        ["C000F009B0001"],
    ),
]


# ==============================================================================
# Minimal local fakes for isolation (tests monkeypatch the module-under-test types)
# ==============================================================================


@dataclass(frozen=True, slots=True)
class _FakeIndexMetadataKey:
    project: str
    index_base: str = "https://pypi.org/simple"


@dataclass(frozen=True, slots=True)
class _FakeWheelKey:
    name: str
    version: str
    tag: str
    origin_uri: str | None = None


@dataclass(frozen=True, slots=True)
class _FakeCoreMetadataKey:
    name: str
    version: str
    tag: str
    file_url: str


class _FakeRequestsResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_payload: Any | None = None,
        content: bytes = b"",
        iter_chunks: Iterable[bytes] = (),
    ) -> None:
        self.status_code = status_code
        self._json_payload = json_payload
        self.content = content
        self._iter_chunks = list(iter_chunks)
        self._raise_for_status_exc: Exception | None = None

    def set_raise_for_status_exc(self, exc: Exception) -> None:
        self._raise_for_status_exc = exc

    def raise_for_status(self) -> None:
        if self._raise_for_status_exc is not None:
            raise self._raise_for_status_exc

    def json(self) -> Any:
        return self._json_payload

    def iter_content(self, *, chunk_size: int) -> Iterable[bytes]:
        # chunk_size is ignored; provided for signature compatibility
        return iter(self._iter_chunks)

    def __enter__(self) -> "_FakeRequestsResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeZipFile:
    """
    Mock zipfile.ZipFile used by strategies; avoids real zip I/O (contract).
    """

    def __init__(self, *_: Any, **__: Any) -> None:
        self._names: list[str] = []
        self._blobs: dict[str, bytes] = {}

    def seed(self, *, names: list[str], blobs: dict[str, bytes]) -> None:
        self._names = list(names)
        self._blobs = dict(blobs)

    def namelist(self) -> list[str]:
        return list(self._names)

    def read(self, member: str) -> bytes:
        return self._blobs[member]

    def __enter__(self) -> "_FakeZipFile":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


# ==============================================================================
# Helper function tests
# ==============================================================================


@pytest.mark.parametrize("value, expected, covers", SAFE_SEGMENT_CASES)
def test_safe_segment(value: str, expected: str, covers: list[str]) -> None:
    # covers: C000F001B0001 / C000F001B0002 (via matrix)
    assert mod._safe_segment(value) == expected


def test_short_hash_is_first_16_of_sha256_hex() -> None:
    # covers: C000F002B0001
    value = "hello"
    expected = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    assert mod._short_hash(value) == expected


@pytest.mark.parametrize("url, expected, covers", URL_BASENAME_CASES)
def test_url_basename_normal_cases(
    url: str, expected: str | None, covers: list[str]
) -> None:
    # covers: C000F003B0001 / C000F003B0002 / C000F003B0003 (via matrix)
    assert mod._url_basename(url) == expected


def test_url_basename_exception_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # covers: C000F003B0004
    def boom(_: str):
        raise RuntimeError("nope")

    monkeypatch.setattr(mod, "urlparse", boom)
    assert mod._url_basename("https://example.com/x") is None


@pytest.mark.parametrize(
    "destination_uri, expected_or_exc, msg_substr, covers",
    REQUIRE_FILE_DESTINATION_CASES,
)
def test_require_file_destination(
    destination_uri: str, expected_or_exc, msg_substr: str | None, covers: list[str]
) -> None:
    # covers: C000F004B0001 / C000F004B0002 (via matrix)
    if expected_or_exc is ValueError:
        with pytest.raises(ValueError) as ei:
            mod._require_file_destination(destination_uri)
        assert msg_substr is not None
        assert msg_substr in str(ei.value)
    else:
        got = mod._require_file_destination(destination_uri)
        assert got == expected_or_exc


def test_ensure_parent_dir_creates_parent(tmp_path: Path) -> None:
    # covers: C000F005B0001
    target = tmp_path / "a" / "b" / "file.txt"
    assert not target.parent.exists()
    mod._ensure_parent_dir(target)
    assert target.parent.exists()
    assert target.parent.is_dir()


@pytest.mark.parametrize("payload_bytes, expected_hex, covers", SHA256_FILE_CASES)
def test_sha256_file(
    tmp_path: Path, payload_bytes: bytes, expected_hex: str, covers: list[str]
) -> None:
    # covers: C000F006B0001 / C000F006B0002 (via matrix)
    p = tmp_path / "x.bin"
    p.write_bytes(payload_bytes)
    assert mod._sha256_file(p) == expected_hex


@pytest.mark.parametrize(
    "index_base, project, expected, covers", SIMPLE_PROJECT_JSON_URL_CASES
)
def test_simple_project_json_url(
    index_base: str, project: str, expected: str, covers: list[str]
) -> None:
    # covers: C000F007B0001
    assert mod._simple_project_json_url(index_base, project) == expected


def test_write_canonical_json_is_deterministic(tmp_path: Path) -> None:
    # covers: C000F008B0001
    p = tmp_path / "out.json"
    payload = {"b": 2, "a": 1}
    mod._write_canonical_json(p, payload)
    assert (
        p.read_text(encoding="utf-8")
        == json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )


@pytest.mark.parametrize("file_url, expected, covers", PEP658_URL_CASES)
def test_pep658_metadata_url(file_url: str, expected: str, covers: list[str]) -> None:
    # covers: C000F009B0001
    assert mod._pep658_metadata_url(file_url) == expected


def test_find_dist_info_metadata_path_raises_when_missing() -> None:
    # covers: C000F010B0001
    class Z:
        def namelist(self) -> list[str]:
            return ["a.txt", "pkg.dist-info/RECORD"]

    with pytest.raises(FileNotFoundError) as ei:
        mod._find_dist_info_metadata_path(Z())  # type: ignore[arg-type]
    assert "dist-info/METADATA" in str(ei.value)


def test_find_dist_info_metadata_path_returns_sorted_first() -> None:
    # covers: C000F010B0002
    class Z:
        def namelist(self) -> list[str]:
            return [
                "b.dist-info/METADATA",
                "a.dist-info/METADATA",
            ]

    assert mod._find_dist_info_metadata_path(Z()) == "a.dist-info/METADATA"  # type: ignore[arg-type]


# ==============================================================================
# Strategy tests (mock external influences at call sites)
# ==============================================================================


def test_pep691_resolve_not_applicable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C001M001B0001
    strat = mod.Pep691IndexMetadataHttpStrategy()
    dest = (tmp_path / "x.json").as_uri()

    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=dest)  # type: ignore[arg-type]


def test_pep691_resolve_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C001M001B0002
    monkeypatch.setattr(mod, "IndexMetadataKey", _FakeIndexMetadataKey)

    captured: dict[str, Any] = {}

    def fake_get(url: str, headers: dict[str, str], timeout: float):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeRequestsResponse(json_payload={"hello": "world"}, content=b"")

    monkeypatch.setattr(mod.requests, "get", fake_get)

    dest_path = tmp_path / "out" / "index.json"
    key = _FakeIndexMetadataKey(
        project="requests", index_base="https://pypi.org/simple/"
    )

    strat = mod.Pep691IndexMetadataHttpStrategy(user_agent="ua-test", timeout_s=1.25)
    rec = strat.resolve(key=key, destination_uri=dest_path.as_uri())

    assert captured["url"] == "https://pypi.org/simple/requests/"
    assert captured["headers"]["Accept"] == "application/vnd.pypi.simple.v1+json"
    assert captured["headers"]["User-Agent"] == "ua-test"
    assert captured["timeout"] == 1.25

    assert dest_path.exists()
    expected_text = json.dumps({"hello": "world"}, indent=2, sort_keys=True) + "\n"
    assert dest_path.read_text(encoding="utf-8") == expected_text

    assert rec is not None
    assert rec.key == key
    assert rec.destination_uri == dest_path.as_uri()
    assert rec.origin_uri == "https://pypi.org/simple/requests/"
    assert rec.size == dest_path.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest_path)
    assert rec.content_hashes == {"sha256": rec.content_sha256}


def test_http_wheel_resolve_not_applicable(tmp_path: Path) -> None:
    # covers: C002M001B0001
    strat = mod.HttpWheelFileStrategy()
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=(tmp_path / "x.whl").as_uri())  # type: ignore[arg-type]


def test_http_wheel_resolve_origin_uri_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C002M001B0002
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)
    strat = mod.HttpWheelFileStrategy()

    key = _FakeWheelKey(name="pkg", version="1.0", tag="py3-none-any", origin_uri=None)
    with pytest.raises(ValueError) as ei:
        strat.resolve(key=key, destination_uri=(tmp_path / "x.whl").as_uri())
    assert "origin_uri" in str(ei.value)


@pytest.mark.parametrize(
    "iter_chunks, covers",
    [
        ([], ["C002M001B0003"]),  # loop 0 iterations
        ([b"abc"], ["C002M001B0004"]),  # loop >=1, chunk truthy
        (
            [b"", b"abc"],
            ["C002M001B0004", "C002M001B0005"],
        ),  # includes falsy chunk and a truthy chunk
    ],
)
def test_http_wheel_resolve_streaming(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    iter_chunks: list[bytes],
    covers: list[str],
) -> None:
    # covers: C002M001B0003 / C002M001B0004 / C002M001B0005 (via matrix rows)
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)

    captured: dict[str, Any] = {}

    def fake_get(url: str, headers: dict[str, str], timeout: float, stream: bool):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["stream"] = stream
        return _FakeRequestsResponse(iter_chunks=iter_chunks)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    strat = mod.HttpWheelFileStrategy(
        user_agent="ua-wheel", timeout_s=9.0, chunk_bytes=3
    )
    key = _FakeWheelKey(
        name="pkg",
        version="1.0",
        tag="py3-none-any",
        origin_uri="https://example.com/pkg.whl",
    )
    dest_path = tmp_path / "d" / "pkg.whl"

    rec = strat.resolve(key=key, destination_uri=dest_path.as_uri())

    assert captured["url"] == "https://example.com/pkg.whl"
    assert captured["headers"]["User-Agent"] == "ua-wheel"
    assert captured["timeout"] == 9.0
    assert captured["stream"] is True

    assert dest_path.exists()
    assert rec is not None
    assert rec.key == key
    assert rec.origin_uri == "https://example.com/pkg.whl"
    assert rec.destination_uri == dest_path.as_uri()
    assert rec.size == dest_path.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest_path)


def test_pep658_resolve_not_applicable_wrong_type(tmp_path: Path) -> None:
    # covers: C003M001B0001
    strat = mod.Pep658CoreMetadataHttpStrategy()
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=(tmp_path / "m").as_uri())  # type: ignore[arg-type]


def test_pep658_resolve_404_not_applicable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C003M001B0002
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)

    def fake_get(url: str, headers: dict[str, str], timeout: float):
        return _FakeRequestsResponse(status_code=404)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    strat = mod.Pep658CoreMetadataHttpStrategy()
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="py3-none-any", file_url="https://files/x.whl"
    )

    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=key, destination_uri=(tmp_path / "meta.txt").as_uri())


def test_pep658_resolve_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C003M001B0003
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)

    content = b"Metadata-Version: 2.1\nName: pkg\nVersion: 1.0\n"

    def fake_get(url: str, headers: dict[str, str], timeout: float):
        return _FakeRequestsResponse(status_code=200, content=content)

    monkeypatch.setattr(mod.requests, "get", fake_get)

    strat = mod.Pep658CoreMetadataHttpStrategy()
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="py3-none-any", file_url="https://files/x.whl"
    )
    dest_path = tmp_path / "meta" / "METADATA"

    rec = strat.resolve(key=key, destination_uri=dest_path.as_uri())

    assert dest_path.read_bytes() == content
    assert rec is not None
    assert rec.key == key
    assert rec.origin_uri == "https://files/x.whl.metadata"
    assert rec.destination_uri == dest_path.as_uri()
    assert rec.size == dest_path.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest_path)


def test_wheel_extracted_metadata_not_applicable_wrong_type(tmp_path: Path) -> None:
    # covers: C004M001B0001
    @dataclass(frozen=True)
    class DummyWheelStrategy:
        def resolve(self, *, key, destination_uri: str):
            raise AssertionError("should not be called")

    strat = mod.WheelExtractedCoreMetadataStrategy(wheel_strategy=DummyWheelStrategy())  # type: ignore[arg-type]
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=(tmp_path / "m").as_uri())  # type: ignore[arg-type]


def test_wheel_extracted_metadata_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C004M001B0002
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)

    # keep tempdir inside tmp_path (no real system temp side effects)
    td = tmp_path / "td"
    td.mkdir(parents=True, exist_ok=True)

    class _FakeTempDir:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def __enter__(self) -> str:
            return str(td)

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(mod.tempfile, "TemporaryDirectory", _FakeTempDir)

    # injected wheel strategy writes "artifact.whl" bytes (file existence check is not used, but keep it realistic)
    class DummyWheelStrategy:
        def resolve(self, *, key: Any, destination_uri: str):
            wheel_path = mod._require_file_destination(destination_uri)
            wheel_path.write_bytes(b"not-a-real-wheel")

    # mock ZipFile I/O (contract)
    zf = _FakeZipFile()
    zf.seed(
        names=["pkg.dist-info/METADATA"],
        blobs={"pkg.dist-info/METADATA": b"EXTRACTED METADATA"},
    )

    def fake_zipfile_ctor(*args: Any, **kwargs: Any) -> _FakeZipFile:
        return zf

    monkeypatch.setattr(mod.zipfile, "ZipFile", fake_zipfile_ctor)

    strat = mod.WheelExtractedCoreMetadataStrategy(wheel_strategy=DummyWheelStrategy())
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="py3-none-any", file_url="https://files/pkg.whl"
    )
    dest_path = tmp_path / "out" / "METADATA"

    rec = strat.resolve(key=key, destination_uri=dest_path.as_uri())

    assert dest_path.read_bytes() == b"EXTRACTED METADATA"
    assert rec is not None
    assert rec.key == key
    assert rec.origin_uri == "https://files/pkg.whl"
    assert rec.destination_uri == dest_path.as_uri()
    assert rec.size == dest_path.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest_path)


def test_direct_uri_wheel_not_applicable_wrong_type(tmp_path: Path) -> None:
    # covers: C005M001B0001
    strat = mod.DirectUriWheelFileStrategy()
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=(tmp_path / "x.whl").as_uri())  # type: ignore[arg-type]


def test_direct_uri_wheel_origin_uri_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C005M001B0002
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)
    strat = mod.DirectUriWheelFileStrategy()
    key = _FakeWheelKey(name="pkg", version="1.0", tag="py3-none-any", origin_uri=None)
    with pytest.raises(ValueError) as ei:
        strat.resolve(key=key, destination_uri=(tmp_path / "x.whl").as_uri())
    assert "origin_uri" in str(ei.value)


def test_direct_uri_wheel_scheme_not_applicable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C005M001B0003
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)
    strat = mod.DirectUriWheelFileStrategy()
    key = _FakeWheelKey(
        name="pkg",
        version="1.0",
        tag="py3-none-any",
        origin_uri="https://example.com/x.whl",
    )
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=key, destination_uri=(tmp_path / "x.whl").as_uri())


def test_direct_uri_wheel_missing_source_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C005M001B0004
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)
    strat = mod.DirectUriWheelFileStrategy()
    key = _FakeWheelKey(
        name="pkg",
        version="1.0",
        tag="py3-none-any",
        origin_uri=str(tmp_path / "nope.whl"),
    )

    with pytest.raises(FileNotFoundError) as ei:
        strat.resolve(key=key, destination_uri=(tmp_path / "dest.whl").as_uri())
    assert "nope.whl" in str(ei.value)


@pytest.mark.parametrize(
    "src_bytes, covers",
    [
        (b"", ["C005M001B0005"]),  # loop 0 iterations (empty file)
        (b"abc", ["C005M001B0006"]),  # loop >=1 iteration
    ],
)
def test_direct_uri_wheel_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, src_bytes: bytes, covers: list[str]
) -> None:
    # covers: C005M001B0005 / C005M001B0006 (via matrix rows)
    monkeypatch.setattr(mod, "WheelKey", _FakeWheelKey)

    src = tmp_path / "src.whl"
    src.write_bytes(src_bytes)

    strat = mod.DirectUriWheelFileStrategy(chunk_bytes=2)
    key = _FakeWheelKey(
        name="pkg", version="1.0", tag="py3-none-any", origin_uri=str(src)
    )
    dest = tmp_path / "out" / "dest.whl"

    rec = strat.resolve(key=key, destination_uri=dest.as_uri())

    assert dest.read_bytes() == src_bytes
    assert rec is not None
    assert rec.origin_uri == str(src)
    assert rec.destination_uri == dest.as_uri()
    assert rec.size == dest.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest)


def test_direct_uri_core_metadata_wrong_type_not_applicable(tmp_path: Path) -> None:
    # covers: C006M001B0001
    strat = mod.DirectUriCoreMetadataStrategy()
    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=object(), destination_uri=(tmp_path / "m").as_uri())  # type: ignore[arg-type]


def test_direct_uri_core_metadata_scheme_not_applicable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C006M001B0002
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)
    strat = mod.DirectUriCoreMetadataStrategy()
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="t", file_url="https://example.com/pkg.whl"
    )

    with pytest.raises(mod.StrategyNotApplicable):
        strat.resolve(key=key, destination_uri=(tmp_path / "m").as_uri())


def test_direct_uri_core_metadata_missing_wheel_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C006M001B0003
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)
    strat = mod.DirectUriCoreMetadataStrategy()
    missing = tmp_path / "nope.whl"
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="t", file_url=str(missing)
    )

    with pytest.raises(FileNotFoundError) as ei:
        strat.resolve(key=key, destination_uri=(tmp_path / "m").as_uri())
    assert "nope.whl" in str(ei.value)


def test_direct_uri_core_metadata_not_a_file_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C006M001B0004
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)
    strat = mod.DirectUriCoreMetadataStrategy()
    d = tmp_path / "dir.whl"
    d.mkdir()
    key = _FakeCoreMetadataKey(name="pkg", version="1.0", tag="t", file_url=str(d))

    with pytest.raises(ValueError) as ei:
        strat.resolve(key=key, destination_uri=(tmp_path / "m").as_uri())
    assert "not a file" in str(ei.value)


def test_direct_uri_core_metadata_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # covers: C006M001B0005
    monkeypatch.setattr(mod, "CoreMetadataKey", _FakeCoreMetadataKey)

    # ensure wheel_path exists and is_file (zip reading is mocked)
    wheel_path = tmp_path / "pkg.whl"
    wheel_path.write_bytes(b"placeholder-wheel")

    zf = _FakeZipFile()
    zf.seed(
        names=["b.dist-info/METADATA", "a.dist-info/METADATA"],
        blobs={
            "a.dist-info/METADATA": b"AAA",
            "b.dist-info/METADATA": b"BBB",
        },
    )

    def fake_zipfile_ctor(*args: Any, **kwargs: Any) -> _FakeZipFile:
        return zf

    monkeypatch.setattr(mod.zipfile, "ZipFile", fake_zipfile_ctor)

    strat = mod.DirectUriCoreMetadataStrategy()
    key = _FakeCoreMetadataKey(
        name="pkg", version="1.0", tag="t", file_url=str(wheel_path)
    )
    dest_path = tmp_path / "out" / "METADATA"

    rec = strat.resolve(key=key, destination_uri=dest_path.as_uri())

    # _find_dist_info_metadata_path picks sorted first -> a.dist-info/METADATA
    assert dest_path.read_bytes() == b"AAA"
    assert rec is not None
    assert rec.origin_uri == str(wheel_path)
    assert rec.destination_uri == dest_path.as_uri()
    assert rec.size == dest_path.stat().st_size
    assert rec.content_sha256 == mod._sha256_file(dest_path)
