from __future__ import annotations

from typing import Any

import pytest

from project_resolution_engine.model import keys as keys_mod, keys

# ==============================================================================
# Case matrix (per TESTING_CONTRACT)
# Each row covers at least one new branch.
# ==============================================================================

BASE_FROM_MAPPING_ERROR_CASES = [
    {
        "name": "missing kind -> ValueError (default NONE case)",
        "mapping": {},
        "exc_type": ValueError,
        # With kind_mapping defaulting to "none", the default-case message includes "'none'".
        "exc_sub": "Unknown artifact key kind: 'none'",
        "covers": ["C001M001B0007"],
    },
    {
        "name": "kind null -> ValueError (enum conversion)",
        "mapping": {"kind": None},
        "exc_type": ValueError,
        # Enum conversion messages vary by Python; assert a stable substring.
        "exc_sub": "valid",
        "covers": ["C001M001B0003"],
    },
    {
        "name": "invalid kind -> ValueError (enum conversion)",
        "mapping": {"kind": "not-a-real-kind"},
        "exc_type": ValueError,
        "exc_sub": "valid",
        "covers": ["C001M001B0003"],
    },
]

BASE_FROM_MAPPING_DISPATCH_CASES = [
    {
        "name": "dispatch index metadata",
        "mapping": {"kind": keys.ArtifactKind.INDEX_METADATA.value, "index_base": "X", "project": "P"},
        "expected_type": keys_mod.IndexMetadataKey,
        "covers": ["C001M001B0004"],
    },
    {
        "name": "dispatch core metadata",
        "mapping": {
            "kind": keys.ArtifactKind.CORE_METADATA.value,
            "name": "n",
            "version": "v",
            "tag": "t",
            "file_url": "u",
        },
        "expected_type": keys_mod.CoreMetadataKey,
        "covers": ["C001M001B0005"],
    },
    {
        "name": "dispatch wheel",
        "mapping": {"kind": keys.ArtifactKind.WHEEL.value, "name": "n", "version": "1", "tag": "py3-none-any"},
        "expected_type": keys_mod.WheelKey,
        "covers": ["C001M001B0006"],
    },
]

INDEX_FROM_MAPPING_ERROR_CASES = [
    {"name": "missing index_base", "mapping": {"project": "P"}, "exc_sub": "index_base", "covers": ["C002M002B0002"]},
    {"name": "missing project", "mapping": {"index_base": "X"}, "exc_sub": "project", "covers": ["C002M002B0003"]},
]

CORE_FROM_MAPPING_ERROR_CASES = [
    {"name": "missing name", "mapping": {"version": "1", "tag": "t", "file_url": "u"}, "exc_sub": "name",
     "covers": ["C003M002B0002"]},
    {"name": "missing version", "mapping": {"name": "n", "tag": "t", "file_url": "u"}, "exc_sub": "version",
     "covers": ["C003M002B0003"]},
    {"name": "missing tag", "mapping": {"name": "n", "version": "1", "file_url": "u"}, "exc_sub": "tag",
     "covers": ["C003M002B0004"]},
    {"name": "missing file_url", "mapping": {"name": "n", "version": "1", "tag": "t"}, "exc_sub": "file_url",
     "covers": ["C003M002B0005"]},
]

WHEEL_VALIDATE_HASH_CASES = [
    # valid
    {
        "name": "sha256 valid + strip/lower",
        "hash_algorithm": "  SHA256  ",
        "content_hash": ("a" * 64) + "  ",
        "expect_hash_spec_prefix": "sha256:",
        "expect_raises": None,
        "covers": ["C004M001B0002"],
    },
    {
        "name": "sha384 valid",
        "hash_algorithm": "sha384",
        "content_hash": "b" * 96,
        "expect_hash_spec_prefix": "sha384:",
        "expect_raises": None,
        "covers": ["C004M001B0004"],
    },
    {
        "name": "sha512 valid",
        "hash_algorithm": "sha512",
        "content_hash": "c" * 128,
        "expect_hash_spec_prefix": "sha512:",
        "expect_raises": None,
        "covers": ["C004M001B0006"],
    },
    # invalid
    {
        "name": "sha256 invalid -> ValueError",
        "hash_algorithm": "sha256",
        "content_hash": "xyz",
        "expect_hash_spec_prefix": None,
        "expect_raises": ("Invalid SHA256 hash", ValueError),
        "covers": ["C004M001B0003"],
    },
    {
        "name": "sha384 invalid -> ValueError",
        "hash_algorithm": "sha384",
        "content_hash": "xyz",
        "expect_hash_spec_prefix": None,
        "expect_raises": ("Invalid SHA384 hash", ValueError),
        "covers": ["C004M001B0005"],
    },
    {
        "name": "sha512 invalid -> ValueError",
        "hash_algorithm": "sha512",
        "content_hash": "xyz",
        "expect_hash_spec_prefix": None,
        "expect_raises": ("Invalid SHA512 hash", ValueError),
        "covers": ["C004M001B0007"],
    },
    # unknown tolerated
    {
        "name": "unknown algorithm tolerated",
        "hash_algorithm": "mD5",
        "content_hash": "whatever",
        "expect_hash_spec_prefix": "md5:",
        "expect_raises": None,
        "covers": ["C004M001B0008"],
    },
]

REQTXT_CASES = [
    {
        "id": "key-none_fmt-none",
        "kwargs": {"key": None, "fmt": None},
        "expected": {"reqtxt": True},
        "covers": [
            "C000F001B0001",
            "C000F001B0003",
            "C000F001B0005",
            "C000F001B0006",
        ],
    },
    {
        "id": "key-set_fmt-none",
        "kwargs": {"key": "k", "fmt": None},
        "expected": {"reqtxt": True, "reqtxt_key": "k"},
        "covers": [
            "C000F001B0001",
            "C000F001B0002",
            "C000F001B0005",
            "C000F001B0006",
        ],
    },
    {
        "id": "key-none_fmt-set",
        "kwargs": {"key": None, "fmt": "f"},
        "expected": {"reqtxt": True, "reqtxt_fmt": "f"},
        "covers": [
            "C000F001B0001",
            "C000F001B0003",
            "C000F001B0004",
            "C000F001B0006",
        ],
    },
    {
        "id": "key-set_fmt-set",
        "kwargs": {"key": "k", "fmt": "f"},
        "expected": {"reqtxt": True, "reqtxt_key": "k", "reqtxt_fmt": "f"},
        "covers": [
            "C000F001B0001",
            "C000F001B0002",
            "C000F001B0004",
            "C000F001B0006",
        ],
    },
]

EMPTY_COLLECTION_CASES = [
    {
        "id": "not-a-collection",
        "v": object(),
        "expected": False,
        "covers": ["C000F002B0001"],
    },
    {
        "id": "empty-list",
        "v": [],
        "expected": True,
        "covers": ["C000F002B0002"],
    },
    {
        "id": "nonempty-list",
        "v": [1],
        "expected": False,
        "covers": ["C000F002B0003"],
    },
]

WHEEL_FROM_MAPPING_REQUIRED_KEY_ERROR_CASES = [
    {"name": "missing name", "mapping": {"version": "1", "tag": "t"}, "exc_sub": "name", "covers": ["C004M017B0002"]},
    {"name": "missing version", "mapping": {"name": "n", "tag": "t"}, "exc_sub": "version",
     "covers": ["C004M017B0003"]},
    {"name": "missing tag", "mapping": {"name": "n", "version": "1"}, "exc_sub": "tag", "covers": ["C004M017B0004"]},
]


# ==============================================================================
# Helpers
# ==============================================================================

def _patch_name_and_version(monkeypatch: pytest.MonkeyPatch, *, normalized_name: str = "my-project",
                            normalized_version: str = "9.9") -> None:
    # Mock external influences at call sites used by keys_mod.
    monkeypatch.setattr(keys_mod, "normalize_project_name", lambda s: normalized_name)

    class _DummyVersion:
        def __init__(self, _s: str) -> None:
            pass

        def __str__(self) -> str:
            return normalized_version

    monkeypatch.setattr(keys_mod, "Version", _DummyVersion)


def _mk_wheel(monkeypatch: pytest.MonkeyPatch, **kwargs) -> keys_mod.WheelKey:
    _patch_name_and_version(monkeypatch)
    base = dict(name="Anything-Here", version="1.2.3", tag="py3-none-any")
    base.update(kwargs)
    return keys_mod.WheelKey(**base)


# ==============================================================================
# Tests
# ==============================================================================


@pytest.mark.parametrize("case", BASE_FROM_MAPPING_ERROR_CASES, ids=lambda c: c["name"])
def test_baseartifactkey_from_mapping_errors(case):
    # Covers: C001M001B0002, C001M001B0003
    with pytest.raises(case["exc_type"]) as ei:
        keys_mod.BaseArtifactKey.from_mapping(case["mapping"])
    assert case["exc_sub"] in str(ei.value)


@pytest.mark.parametrize("case", BASE_FROM_MAPPING_DISPATCH_CASES, ids=lambda c: c["name"])
def test_baseartifactkey_from_mapping_dispatch(case, monkeypatch):
    # Covers: C001M001B0004, C001M001B0005, C001M001B0006 (and WheelKey.from_mapping path)
    # Keep WheelKey post-init deterministic.
    _patch_name_and_version(monkeypatch)

    obj = keys_mod.BaseArtifactKey.from_mapping(case["mapping"])
    assert isinstance(obj, case["expected_type"])


def test_indexmetadatakey_to_mapping():
    # Covers: C002M001B0001
    k = keys_mod.IndexMetadataKey(project="proj", index_base="https://example/simple")
    assert k.to_mapping() == {
        "kind": keys.ArtifactKind.INDEX_METADATA.value,
        "index_base": "https://example/simple",
        "project": "proj",
    }


@pytest.mark.parametrize("case", INDEX_FROM_MAPPING_ERROR_CASES, ids=lambda c: c["name"])
def test_indexmetadatakey_from_mapping_keyerrors(case):
    # Covers: C002M002B0002, C002M002B0003
    with pytest.raises(KeyError) as ei:
        keys_mod.IndexMetadataKey.from_mapping(case["mapping"])
    assert case["exc_sub"] in str(ei.value)


def test_indexmetadatakey_from_mapping_success():
    # Covers: C002M002B0001
    k = keys_mod.IndexMetadataKey.from_mapping({"index_base": "X", "project": "P"})
    assert k.index_base == "X"
    assert k.project == "P"
    assert k.kind == keys.ArtifactKind.INDEX_METADATA


def test_coremetadatakey_to_mapping():
    # Covers: C003M001B0001
    k = keys_mod.CoreMetadataKey(name="n", version="v", tag="t", file_url="u")
    assert k.to_mapping() == {
        "kind": keys.ArtifactKind.CORE_METADATA.value,
        "name": "n",
        "version": "v",
        "tag": "t",
        "file_url": "u",
    }


@pytest.mark.parametrize("case", CORE_FROM_MAPPING_ERROR_CASES, ids=lambda c: c["name"])
def test_coremetadatakey_from_mapping_keyerrors(case):
    # Covers: C003M002B0002..B0005
    with pytest.raises(KeyError) as ei:
        keys_mod.CoreMetadataKey.from_mapping(case["mapping"])
    assert case["exc_sub"] in str(ei.value)


def test_coremetadatakey_from_mapping_success():
    # Covers: C003M002B0001
    k = keys_mod.CoreMetadataKey.from_mapping({"name": "n", "version": "1", "tag": "t", "file_url": "u"})
    assert (k.name, k.version, k.tag, k.file_url) == ("n", "1", "t", "u")
    assert k.kind == keys.ArtifactKind.CORE_METADATA


def test_wheelkey_post_init_normalizes_name_and_version(monkeypatch):
    # Covers: C004M002B0001, C004M002B0002, C004M002B0004, and C004M001B0001 (early return since no hash fields)
    _patch_name_and_version(monkeypatch, normalized_name="my-project", normalized_version="9.9")
    wk = keys_mod.WheelKey(name="Whatever", version="not-used", tag="py3-none-any")
    assert wk.name == "my-project"
    assert wk.version == "9.9"
    assert wk._hash_spec is None  # no hash_algorithm/content_hash provided -> early return path


def test_wheelkey_post_init_invalid_version_branch(monkeypatch):
    # Covers: C004M002B0003
    monkeypatch.setattr(keys_mod, "normalize_project_name", lambda s: "my-project")

    def _raise_invalid(_s: str):
        raise keys_mod.InvalidVersion("nope")

    monkeypatch.setattr(keys_mod, "Version", _raise_invalid)

    wk = keys_mod.WheelKey(name="Whatever", version="definitely-not-a-version", tag="py3-none-any")
    assert wk.version == "definitely-not-a-version"


@pytest.mark.parametrize("case", WHEEL_VALIDATE_HASH_CASES, ids=lambda c: c["name"])
def test_wheelkey_validate_hash_and_set_spec(case, monkeypatch):
    # Covers: C004M001B0002..B0008 (via __post_init__ call into _validate_hash_and_set_spec)
    _patch_name_and_version(monkeypatch)

    if case["expect_raises"] is not None:
        sub, exc_type = case["expect_raises"]
        with pytest.raises(exc_type) as ei:
            keys_mod.WheelKey(
                name="n",
                version="1",
                tag="py3-none-any",
                hash_algorithm=case["hash_algorithm"],
                content_hash=case["content_hash"],
            )
        assert sub in str(ei.value)
        return

    wk = keys_mod.WheelKey(
        name="n",
        version="1",
        tag="py3-none-any",
        hash_algorithm=case["hash_algorithm"],
        content_hash=case["content_hash"],
    )
    assert wk._hash_spec is not None
    assert wk._hash_spec.startswith(case["expect_hash_spec_prefix"])


@pytest.mark.parametrize(
    "case",
    REQTXT_CASES,
    ids=[c["id"] for c in REQTXT_CASES],
)
def test_reqtxt_case_matrix(case: dict[str, Any]) -> None:
    # Covers: Needs an update
    got = keys.reqtxt(**case["kwargs"])
    assert got == case["expected"]


@pytest.mark.parametrize(
    "case",
    EMPTY_COLLECTION_CASES,
    ids=[c["id"] for c in EMPTY_COLLECTION_CASES],
)
def test__is_empty_collection_case_matrix(case: dict[str, Any]) -> None:
    # Covers: C000F002B0001-B0003 (see EMPTY_COLLECTION_CASES[*]["covers"])
    got = keys._is_empty_collection(case["v"])
    assert got is case["expected"]


def test_normalize_project_name_delegates_to_canonicalize_name(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers: C000F003B0001
    calls: list[str] = []

    def _fake_canon(s: str) -> str:
        calls.append(s)
        return "normalized!"

    monkeypatch.setattr(keys, "canonicalize_name", _fake_canon)

    assert keys.normalize_project_name("Some_Project") == "normalized!"
    assert calls == ["Some_Project"]


def test_wheelkey_set_dependency_ids_set_and_error(monkeypatch):
    # Covers: C004M003B0002, C004M003B0001
    wk = _mk_wheel(monkeypatch)

    dep1 = _mk_wheel(monkeypatch, tag="cp311-manylinux_x86_64")
    dep2 = _mk_wheel(monkeypatch, tag="cp310-manylinux_x86_64")

    wk.set_dependency_ids([dep1, dep2])
    assert wk.dependency_ids == frozenset({dep1.identifier, dep2.identifier})

    with pytest.raises(ValueError) as ei:
        wk.set_dependency_ids([])
    assert "dependency_ids is already set" in str(ei.value)


def test_wheelkey_set_origin_uri_set_and_error(monkeypatch):
    # Covers: C004M004B0001, C004M004B0002
    wk = _mk_wheel(monkeypatch)
    wk.set_origin_uri("https://example/wheel.whl")
    assert wk.origin_uri == "https://example/wheel.whl"

    with pytest.raises(ValueError) as ei:
        wk.set_origin_uri("https://example/other.whl")
    assert "origin_uri is already set" in str(ei.value)


def test_wheelkey_set_content_hash_set_and_already_set_error(monkeypatch):
    # Covers: C004M005B0002, C004M005B0001 (and reuses hash validation success path)
    wk = _mk_wheel(monkeypatch)
    wk.set_content_hash(hash_algorithm=" SHA256 ", content_hash=" " + ("a" * 64) + " ")
    assert wk._hash_spec == "sha256:" + ("a" * 64)

    with pytest.raises(ValueError) as ei:
        wk.set_content_hash(hash_algorithm="sha256", content_hash="b" * 64)
    assert "content hash is already set" in str(ei.value)


def test_wheelkey_set_content_hash_invalid_hash_raises(monkeypatch):
    # Covers: C004M005B0002 + C004M001B0003 (invalid sha256)
    wk = _mk_wheel(monkeypatch)
    with pytest.raises(ValueError) as ei:
        wk.set_content_hash(hash_algorithm="sha256", content_hash="not-hex")
    assert "Invalid SHA256 hash" in str(ei.value)


def test_wheelkey_convenience_and_comparisons(monkeypatch):
    # Covers: C004M006B0001, C004M007B0001, C004M008B0001, C004M009B0001,
    #         C004M010B0001, C004M010B0002, C004M011B0001, C004M012B0001
    _patch_name_and_version(monkeypatch, normalized_name="my-project", normalized_version="1")
    a = keys_mod.WheelKey(name="X", version="Y", tag="a")
    b = keys_mod.WheelKey(name="X", version="Y", tag="b")

    assert a._proj_name_with_underscores() == "my_project"
    assert a.identifier == "my_project-1-a"
    assert a.as_tuple() == ("my-project", "1", "a")
    assert a < b

    assert (a == object()) is False
    assert (a == keys_mod.WheelKey(name="X", version="Y", tag="a")) is True

    assert isinstance(hash(a), int)
    assert str(a) == a.identifier


def test_wheelkey_requirement_str_branches(monkeypatch):
    # Covers: C004M013B0001, C004M013B0002, C004M013B0003
    wk = _mk_wheel(monkeypatch)

    # origin_uri missing
    with pytest.raises(ValueError) as ei1:
        _ = wk.requirement_str
    assert "origin_uri is required" in str(ei1.value)

    # _hash_spec missing (set origin_uri only)
    wk.set_origin_uri("https://example/wheel.whl")
    with pytest.raises(ValueError) as ei2:
        _ = wk.requirement_str
    assert "_hash_spec is required" in str(ei2.value)

    # success (set hash too)
    wk.set_content_hash(hash_algorithm="sha256", content_hash="a" * 64)
    s = wk.requirement_str
    assert "my-project" in s
    assert "https://example/wheel.whl" in s
    assert "--hash=sha256:" + ("a" * 64) in s


def test_wheelkey_requirement_str_basic(monkeypatch):
    # Covers: C004M014B0001
    _patch_name_and_version(monkeypatch, normalized_name="my-project", normalized_version="2")
    wk = keys_mod.WheelKey(name="X", version="Y", tag="py3-none-any")
    assert wk.requirement_str_basic == "my-project==2"


def test_wheelkey_req_txt_block_branches(monkeypatch):
    # Covers: C004M015B0001, C004M015B0002, C004M015B0003
    wk = _mk_wheel(monkeypatch)

    with pytest.raises(ValueError) as ei1:
        _ = wk.req_txt_block
    assert "origin_uri is required" in str(ei1.value)

    wk.set_origin_uri("https://example/wheel.whl")
    with pytest.raises(ValueError) as ei2:
        _ = wk.req_txt_block
    assert "_hash_spec is required" in str(ei2.value)

    wk.set_content_hash(hash_algorithm="sha256", content_hash="a" * 64)

    block = wk.req_txt_block
    assert block.splitlines() == [
        "# name: my-project",
        "# version: 9.9",
        "# tag: py3-none-any",
        "# origin_uri: https://example/wheel.whl",
        "# hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        wk.requirement_str,
    ]


def test_wheelkey_to_mapping_dependency_and_extras_branches(monkeypatch):
    # Covers: C004M016B0002, C004M016B0004, C004M016B0005 (base mapping)
    wk1 = _mk_wheel(monkeypatch, satisfied_tags=frozenset({"t1", "t2"}))
    m1 = wk1.to_mapping()
    assert m1["dependencies"] is None
    assert m1["extras"] is None
    assert sorted(m1["satisfied_tags"]) == ["t1", "t2"]

    # Covers: C004M016B0001, C004M016B0003
    wk2 = _mk_wheel(monkeypatch, dependency_ids=frozenset({"d1"}), extras=frozenset({"x"}))
    m2 = wk2.to_mapping()
    assert m2["dependencies"] == ["d1"]
    assert m2["extras"] == ["x"]


@pytest.mark.parametrize("case", WHEEL_FROM_MAPPING_REQUIRED_KEY_ERROR_CASES, ids=lambda c: c["name"])
def test_wheelkey_from_mapping_required_keyerrors(case, monkeypatch):
    # Covers: C004M017B0002..B0004
    _patch_name_and_version(monkeypatch)
    with pytest.raises(KeyError) as ei:
        keys_mod.WheelKey.from_mapping(case["mapping"])
    assert case["exc_sub"] in str(ei.value)


def test_wheelkey_from_mapping_dependency_and_extras_branches(monkeypatch):
    # Covers: C004M017B0005, C004M017B0007, C004M017B0009, C004M017B0010
    _patch_name_and_version(monkeypatch)

    wk = keys_mod.WheelKey.from_mapping(
        {
            "name": "n",
            "version": "v",
            "tag": "py3-none-any",
            "dependencies": ["d1", "d2"],
            "extras": ["x1"],
            # satisfied_tags omitted to hit default-empty path too, but we cover that separately below
        }
    )
    assert wk.dependency_ids == frozenset({"d1", "d2"})
    assert wk.extras == frozenset({"x1"})
    assert wk.satisfied_tags == frozenset()


def test_wheelkey_from_mapping_none_dependencies_and_extras(monkeypatch):
    # Covers: C004M017B0006, C004M017B0008, C004M017B0009
    _patch_name_and_version(monkeypatch)

    wk = keys_mod.WheelKey.from_mapping({"name": "n", "version": "v", "tag": "py3-none-any"})
    assert wk.dependency_ids is None
    assert wk.extras is None
    assert wk.satisfied_tags == frozenset()
