from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from project_resolution_engine import repository as uut


# ==============================================================================
# Helpers (not test classes; allowed)
# ==============================================================================

@dataclass(frozen=True, slots=True)
class _FakeKey:
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.payload)


class _FakeBaseArtifactKey:
    """
    Minimal stand-in that matches the call surface used by ArtifactRecord.from_mapping:
      - BaseArtifactKey.from_mapping(mapping) -> key instance with .to_mapping()
    """

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> _FakeKey:
        return _FakeKey(mapping)


# ==============================================================================
# Case matrices (mandatory per contract)
# ==============================================================================

TO_MAPPING_CASES = [
    {
        "id": "no-content-hashes",
        "content_hashes": {},
        "expect_has_content_hashes": False,
        "covers": ["C005M001B0001", "C005M001B0003", "C005M001B0004"],
    },
    {
        "id": "has-content-hashes",
        "content_hashes": {"sha256": "abc"},
        "expect_has_content_hashes": True,
        "covers": ["C005M001B0001", "C005M001B0002", "C005M001B0004"],
    },
]

FROM_MAPPING_SUCCESS_CASES = [
    {
        "id": "default-source_default-hashes",
        "mapping": {
            "key": {"k": "v"},
            "destination_uri": "dst://x",
            "origin_uri": "src://x",
            # no "source"
            # no "content_hashes"
        },
        "expect_source": uut.ArtifactSource.OTHER,
        "expect_hashes": {},
        "covers": [
            "C005M002B0001",
            "C005M002B0004",
            "C005M002B0008",
        ],
    },
    {
        "id": "explicit-source_explicit-hashes",
        "mapping": {
            "key": {"k": "v"},
            "destination_uri": "dst://x",
            "origin_uri": "src://x",
            "source": uut.ArtifactSource.HTTP_PEP691.value,
            "content_hashes": {"sha256": "abc"},
        },
        "expect_source": uut.ArtifactSource.HTTP_PEP691,
        "expect_hashes": {"sha256": "abc"},
        "covers": [
            "C005M002B0002",
            "C005M002B0005",
            "C005M002B0008",
        ],
    },
]

FROM_MAPPING_MISSING_REQUIRED_CASES = [
    {
        "id": "missing-key",
        "mapping": {"destination_uri": "dst://x", "origin_uri": "src://x"},
        "missing": "key",
        "covers": ["C005M002B0003"],
    },
    {
        "id": "missing-destination_uri",
        "mapping": {"key": {"k": "v"}, "origin_uri": "src://x"},
        "missing": "destination_uri",
        "covers": ["C005M002B0003"],
    },
    {
        "id": "missing-origin_uri",
        "mapping": {"key": {"k": "v"}, "destination_uri": "dst://x"},
        "missing": "origin_uri",
        "covers": ["C005M002B0003"],
    },
]

FROM_MAPPING_INVALID_SOURCE_CASES = [
    {
        "id": "invalid-source",
        "mapping": {
            "key": {"k": "v"},
            "destination_uri": "dst://x",
            "origin_uri": "src://x",
            "source": "not-a-real-source",
        },
        "substr": "not-a-real-source",
        "covers": ["C005M002B0006"],
    }
]


# ==============================================================================
# Tests
# ==============================================================================


# noinspection PyTypeChecker
def test_artifact_repository_close_is_noop() -> None:
    # Covers: C003M005B0001
    assert uut.ArtifactRepository.close(object()) is None


# noinspection PyTypeChecker
def test_abstract_placeholder_methods_execute_as_noops_when_called_unbound() -> None:
    """
    Covers the placeholder "..." method bodies in the ABCs.

    These methods are abstract (so they are not meant to be invoked via instances),
    but the branch ledger includes their bodies, and they are still callable as
    unbound functions. Calling them this way exercises only this module's code,
    without involving any external dependencies.
    """
    # Covers: C003M001B0001, C003M002B0001, C003M003B0001, C003M004B0001, C004M001B0001
    dummy_key = object()
    dummy_record = object()

    assert uut.ArtifactRepository.get(object(), dummy_key) is None
    assert uut.ArtifactRepository.put(object(), dummy_record) is None
    assert uut.ArtifactRepository.delete(object(), dummy_key) is None
    assert uut.ArtifactRepository.allocate_destination_uri(object(), dummy_key) is None

    assert uut.ArtifactResolver.resolve(object(), dummy_key, "dst://x") is None


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "case",
    TO_MAPPING_CASES,
    ids=[c["id"] for c in TO_MAPPING_CASES],
)
def test_artifact_record_to_mapping(case: dict[str, Any]) -> None:
    # Covers: C005M001B0001-B0004 (see TO_MAPPING_CASES[*]["covers"])
    key = _FakeKey({"kind": "fake", "id": "k1"})
    record = uut.ArtifactRecord(
        key=key,
        destination_uri="dst://x",
        origin_uri="src://x",
        source=uut.ArtifactSource.HTTP_WHEEL,
        content_sha256="deadbeef",
        size=123,
        created_at_epoch_s=456.0,
        content_hashes=case["content_hashes"],
    )

    got = record.to_mapping()

    assert got["key"] == {"kind": "fake", "id": "k1"}
    assert got["destination_uri"] == "dst://x"
    assert got["origin_uri"] == "src://x"
    assert got["source"] == uut.ArtifactSource.HTTP_WHEEL.value
    assert got["content_sha256"] == "deadbeef"
    assert got["size"] == 123
    assert got["created_at_epoch_s"] == 456.0

    if case["expect_has_content_hashes"]:
        assert got["content_hashes"] == case["content_hashes"]
    else:
        assert "content_hashes" not in got


@pytest.mark.parametrize(
    "case",
    FROM_MAPPING_SUCCESS_CASES,
    ids=[c["id"] for c in FROM_MAPPING_SUCCESS_CASES],
)
def test_artifact_record_from_mapping_success(monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]) -> None:
    # Covers: C005M002B0001, B0002, B0004, B0005, B0008 (see FROM_MAPPING_SUCCESS_CASES[*]["covers"])
    monkeypatch.setattr(uut, "BaseArtifactKey", _FakeBaseArtifactKey)

    # Ensure content_hashes is copied (not referenced) when provided
    mapping = dict(case["mapping"])
    if "content_hashes" in mapping:
        mapping["content_hashes"] = dict(mapping["content_hashes"])  # ensure a mutable input we can mutate later
        original_hashes = mapping["content_hashes"]
    else:
        original_hashes = None

    rec = uut.ArtifactRecord.from_mapping(mapping)

    assert isinstance(rec.key, _FakeKey)
    assert rec.destination_uri == case["mapping"]["destination_uri"]
    assert rec.origin_uri == case["mapping"]["origin_uri"]
    assert rec.source == case["expect_source"]
    assert rec.content_hashes == case["expect_hashes"]

    if original_hashes is not None:
        original_hashes["sha256"] = "CHANGED"
        assert rec.content_hashes == case["expect_hashes"]  # unchanged due to dict() copy


@pytest.mark.parametrize(
    "case",
    FROM_MAPPING_MISSING_REQUIRED_CASES,
    ids=[c["id"] for c in FROM_MAPPING_MISSING_REQUIRED_CASES],
)
def test_artifact_record_from_mapping_missing_required_raises_keyerror(
        monkeypatch: pytest.MonkeyPatch,
        case: dict[str, Any],
) -> None:
    # Covers: C005M002B0003
    monkeypatch.setattr(uut, "BaseArtifactKey", _FakeBaseArtifactKey)

    with pytest.raises(KeyError) as excinfo:
        uut.ArtifactRecord.from_mapping(case["mapping"])

    # KeyError stringification can vary; assert the missing field name is present.
    assert case["missing"] in str(excinfo.value)


@pytest.mark.parametrize(
    "case",
    FROM_MAPPING_INVALID_SOURCE_CASES,
    ids=[c["id"] for c in FROM_MAPPING_INVALID_SOURCE_CASES],
)
def test_artifact_record_from_mapping_invalid_source_raises_valueerror(
        monkeypatch: pytest.MonkeyPatch,
        case: dict[str, Any],
) -> None:
    # Covers: C005M002B0006
    monkeypatch.setattr(uut, "BaseArtifactKey", _FakeBaseArtifactKey)

    with pytest.raises(ValueError) as excinfo:
        uut.ArtifactRecord.from_mapping(case["mapping"])

    assert case["substr"] in str(excinfo.value)


def test_artifact_record_from_mapping_propagates_key_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: C005M002B0007
    class _ExplodingBaseArtifactKey:
        @classmethod
        def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> _FakeKey:
            raise ValueError("boom-from-key")

    monkeypatch.setattr(uut, "BaseArtifactKey", _ExplodingBaseArtifactKey)

    mapping = {
        "key": {"k": "v"},
        "destination_uri": "dst://x",
        "origin_uri": "src://x",
    }

    with pytest.raises(ValueError) as excinfo:
        uut.ArtifactRecord.from_mapping(mapping)

    assert "boom-from-key" in str(excinfo.value)
