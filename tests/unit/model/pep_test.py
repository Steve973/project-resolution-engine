from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import pytest

import project_resolution_engine.model.pep as pep

# ==============================================================================
# CASE MATRICES (per TESTING_CONTRACT.md)
# ==============================================================================

COERCE_FIELD_CASES = [
    # Covers: C000F001B0001
    (
        {"a": "b"},
        {"a": "b"},
        ["C000F001B0001"],
    ),
    # Covers: C000F001B0002
    (
        True,
        True,
        ["C000F001B0002"],
    ),
    # Covers: C000F001B0003
    (
        "nope",
        False,
        ["C000F001B0003"],
    ),
]

PEP658_FROM_MAPPING_CASES = [
    # Covers: C001M002B0001, C001M002B0003, C001M002B0005
    (
        {"name": "Pkg", "version": 1, "requires_python": ">=3.8", "requires_dist": ["a", "b"]},
        ("Pkg", "1", ">=3.8", frozenset({"a", "b"})),
        ["C001M002B0001", "C001M002B0003", "C001M002B0005"],
    ),
    # Covers: C001M002B0002, C001M002B0004, C001M002B0005
    (
        {"name": "Pkg", "version": "2", "requires_python": "", "requires_dist": None},
        ("Pkg", "2", None, frozenset()),
        ["C001M002B0002", "C001M002B0004", "C001M002B0005"],
    ),
]

PEP658_FROM_CORE_METADATA_TEXT_CASES = [
    # Covers: C001M003B0002, C001M003B0004, C001M003B0006, C001M003B0008, C001M003B0009, C001M003B0013
    (
        # msg.get("Name") -> None, msg.get("Version") -> None, rp_raw -> None, msg.get_all("Requires-Dist") -> None
        {"Name": None, "Version": None, "Requires-Python": None},
        None,
        ("", "", None, frozenset()),
        [
            "C001M003B0002",
            "C001M003B0004",
            "C001M003B0006",
            "C001M003B0008",
            "C001M003B0009",
            "C001M003B0013",
        ],
    ),
    # Covers: C001M003B0001, C001M003B0003, C001M003B0005, C001M003B0007, C001M003B0010, C001M003B0011, C001M003B0012, C001M003B0013
    (
        {"Name": "  Foo  ", "Version": " 1.0 ", "Requires-Python": "  >=3.11  "},
        [" dep1 ", "   ", "\tdep2"],
        ("Foo", "1.0", ">=3.11", frozenset({"dep1", "dep2"})),
        [
            "C001M003B0001",
            "C001M003B0003",
            "C001M003B0005",
            "C001M003B0007",
            "C001M003B0010",
            "C001M003B0011",
            "C001M003B0012",
            "C001M003B0013",
        ],
    ),
]

PEP691_METADATA_TO_MAPPING_CASES = [
    # Covers: C003M001B0001, C003M001B0003
    (
        "demo",
        [],
        None,
        {"name": "demo", "files": [], "last_serial": None},
        ["C003M001B0001", "C003M001B0003"],
    ),
    # Covers: C003M001B0002, C003M001B0003
    (
        "demo",
        [
            pep.Pep691FileMetadata(
                filename="x.whl",
                url="https://example.invalid/x.whl",
                hashes={"sha256": "abc"},
                requires_python=None,
                yanked=False,
                core_metadata=False,
                data_dist_info_metadata=False,
            )
        ],
        7,
        {"name": "demo", "files": [{"filename": "x.whl"}], "last_serial": 7},  # partial expected (asserted below)
        ["C003M001B0002", "C003M001B0003"],
    ),
]

PEP691_METADATA_FROM_MAPPING_CASES = [
    # Covers: C003M002B0001, C003M002B0006, C003M002B0007
    (
        {"name": "n", "files": [], "last_serial": None},
        ("n", 0, None),
        ["C003M002B0001", "C003M002B0006", "C003M002B0007"],
    ),
    # Covers: C003M002B0002, C003M002B0003, C003M002B0004, C003M002B0005, C003M002B0007
    (
        {
            "name": "n",
            "files": [
                {
                    "filename": "a.whl",
                    "url": "https://example.invalid/a.whl",
                    "hashes": {"sha256": "deadbeef"},
                    "requires_python": ">=3.10",
                    "yanked": False,
                    "core-metadata": {"sha256": "111"},
                    "data-dist-info-metadata": True,
                },
                "not-a-mapping",
            ],
            "last_serial": "42",
        },
        ("n", 1, 42),
        ["C003M002B0002", "C003M002B0003", "C003M002B0004", "C003M002B0005", "C003M002B0007"],
    ),
]


# ==============================================================================
# Helpers (local to test module; no external side effects)
# ==============================================================================

@dataclass(frozen=True)
class _FakeMessage:
    headers: Mapping[str, Any]
    requires_dist_headers: Sequence[str] | None

    def get(self, key: str, default: Any = None) -> Any:
        value = self.headers.get(key, default)
        return value

    def get_all(self, key: str) -> Sequence[str] | None:
        if key == "Requires-Dist":
            return self.requires_dist_headers
        return None


class _FakeParser:
    def __init__(self, msg: _FakeMessage) -> None:
        self._msg = msg

    def parsestr(self, _text: str) -> _FakeMessage:
        return self._msg


# ==============================================================================
# Tests
# ==============================================================================

@pytest.mark.parametrize("value, expected, covers", COERCE_FIELD_CASES)
def test__coerce_field_cases(value: Any, expected: Any, covers: list[str]) -> None:
    # Covers (per-row): see COERCE_FIELD_CASES
    out = pep._coerce_field(value)
    assert out == expected


@pytest.mark.parametrize("mapping, expected, covers", PEP658_FROM_MAPPING_CASES)
def test_pep658metadata_from_mapping_cases(
        mapping: Mapping[str, Any],
        expected: tuple[str, str, str | None, frozenset[str]],
        covers: list[str],
) -> None:
    # Covers (per-row): see PEP658_FROM_MAPPING_CASES
    m = pep.Pep658Metadata.from_mapping(mapping)
    exp_name, exp_version, exp_requires_python, exp_requires_dist = expected

    assert m.name == exp_name
    assert m.version == exp_version
    assert m.requires_python == exp_requires_python
    assert m.requires_dist == exp_requires_dist


def test_pep658metadata_to_mapping_emits_requires_dist_as_list() -> None:
    # Covers: C001M001B0001
    m = pep.Pep658Metadata(
        name="pkg",
        version="1.2.3",
        requires_python=None,
        requires_dist=frozenset({"a", "b"}),
    )
    out = m.to_mapping()

    assert out["name"] == "pkg"
    assert out["version"] == "1.2.3"
    assert out["requires_python"] is None
    assert isinstance(out["requires_dist"], list)
    assert set(out["requires_dist"]) == {"a", "b"}


@pytest.mark.parametrize("headers, rd_headers, expected, covers", PEP658_FROM_CORE_METADATA_TEXT_CASES)
def test_pep658metadata_from_core_metadata_text_cases(
        monkeypatch: pytest.MonkeyPatch,
        headers: Mapping[str, Any],
        rd_headers: Sequence[str] | None,
        expected: tuple[str, str, str | None, frozenset[str]],
        covers: list[str],
) -> None:
    # Covers (per-row): see PEP658_FROM_CORE_METADATA_TEXT_CASES
    fake_msg = _FakeMessage(headers=headers, requires_dist_headers=rd_headers)

    # Mock external influence at the call site used by the unit under test.
    monkeypatch.setattr(pep, "Parser", lambda: _FakeParser(fake_msg))

    m = pep.Pep658Metadata.from_core_metadata_text("ignored by fake parser")

    exp_name, exp_version, exp_requires_python, exp_requires_dist = expected
    assert m.name == exp_name
    assert m.version == exp_version
    assert m.requires_python == exp_requires_python
    assert m.requires_dist == exp_requires_dist


def test_pep691filemetadata_from_mapping_coerces_core_metadata_fields() -> None:
    # Covers: C002M002B0001, C002M002B0002, C002M002B0003
    # Also exercises _coerce_field via those call sites (already fully covered separately).
    mapping = {
        "filename": "x.whl",
        "url": "https://example.invalid/x.whl",
        "hashes": {"sha256": "abc"},
        "requires_python": None,
        "yanked": False,
        "core-metadata": {"sha256": "111"},
        "data-dist-info-metadata": True,
    }

    m = pep.Pep691FileMetadata.from_mapping(mapping)

    assert m.filename == "x.whl"
    assert m.url == "https://example.invalid/x.whl"
    assert m.hashes == {"sha256": "abc"}
    assert m.requires_python is None
    assert m.yanked is False
    assert m.core_metadata == {"sha256": "111"}
    assert m.data_dist_info_metadata is True


def test_pep691filemetadata_to_mapping_copies_hashes_to_plain_dict() -> None:
    # Covers: C002M001B0001
    m = pep.Pep691FileMetadata(
        filename="x.whl",
        url="https://example.invalid/x.whl",
        hashes={"sha256": "abc"},
        requires_python=None,
        yanked=False,
        core_metadata=False,
        data_dist_info_metadata=False,
    )

    out = m.to_mapping()
    assert out["hashes"] == {"sha256": "abc"}
    assert isinstance(out["hashes"], dict)


@pytest.mark.parametrize("name, files, last_serial, _expected, covers", PEP691_METADATA_TO_MAPPING_CASES)
def test_pep691metadata_to_mapping_cases(
        name: str,
        files: Sequence[pep.Pep691FileMetadata],
        last_serial: int | None,
        _expected: Mapping[str, Any],
        covers: list[str],
) -> None:
    # Covers (per-row): see PEP691_METADATA_TO_MAPPING_CASES
    m = pep.Pep691Metadata(name=name, files=files, last_serial=last_serial)
    out = m.to_mapping()

    assert out["name"] == name
    assert out["last_serial"] == last_serial

    if not files:
        # Covers: C003M001B0001
        assert out["files"] == []
    else:
        # Covers: C003M001B0002
        assert isinstance(out["files"], list)
        assert len(out["files"]) == 1
        assert out["files"][0]["filename"] == "x.whl"


@pytest.mark.parametrize("mapping, expected, covers", PEP691_METADATA_FROM_MAPPING_CASES)
def test_pep691metadata_from_mapping_cases(
        mapping: Mapping[str, Any],
        expected: tuple[str, int, int | None],
        covers: list[str],
) -> None:
    # Covers (per-row): see PEP691_METADATA_FROM_MAPPING_CASES
    m = pep.Pep691Metadata.from_mapping(mapping)

    exp_name, exp_file_count, exp_last_serial = expected
    assert m.name == exp_name
    assert len(m.files) == exp_file_count
    assert m.last_serial == exp_last_serial

    if exp_file_count == 1:
        # Covers: C003M002B0003, C003M002B0004
        f0 = m.files[0]
        assert isinstance(f0, pep.Pep691FileMetadata)
        assert f0.filename == "a.whl"
        assert f0.core_metadata == {"sha256": "111"}  # Mapping case -> dict preserved by _coerce_field
        assert f0.data_dist_info_metadata is True
