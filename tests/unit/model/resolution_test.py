from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest
from packaging.markers import Marker
from packaging.specifiers import SpecifierSet

from project_resolution_engine.model import resolution
from project_resolution_engine.model.resolution import (
    ResolutionPolicy,
    RequiresDistUrlPolicy,
    YankedWheelPolicy,
    PreReleasePolicy,
    InvalidRequiresDistPolicy,
    ResolutionEnv,
    ArtifactResolutionError,
    WheelSpec,
)

# ==============================================================================
# CASE MATRICES (per TESTING_CONTRACT.md)
# ==============================================================================

POLICY_TO_MAPPING_CASES = [
    # Covers: C006M001B0002, C006M001B0003
    (
        ResolutionPolicy(
            allowed_requires_dist_url_schemes=None,
            requires_dist_url_policy=RequiresDistUrlPolicy.IGNORE,
            yanked_wheel_policy=YankedWheelPolicy.SKIP,
            prerelease_policy=PreReleasePolicy.DEFAULT,
            invalid_requires_dist_policy=InvalidRequiresDistPolicy.SKIP,
        ),
        None,
        ["C006M001B0002", "C006M001B0003"],
    ),
    # Covers: C006M001B0001, C006M001B0003
    (
        ResolutionPolicy(
            allowed_requires_dist_url_schemes=frozenset({"https", "http"}),
            requires_dist_url_policy=RequiresDistUrlPolicy.HONOR,
            yanked_wheel_policy=YankedWheelPolicy.ALLOW,
            prerelease_policy=PreReleasePolicy.ALLOW,
            invalid_requires_dist_policy=InvalidRequiresDistPolicy.RAISE,
        ),
        ["http", "https"],
        ["C006M001B0001", "C006M001B0003"],
    ),
]

POLICY_FROM_MAPPING_SUCCESS_CASES = [
    # Covers: C006M002B0001, C006M002B0004, C006M002B0006, C006M002B0008, C006M002B0010, C006M002B0012
    (
        {
            "allowed_requires_dist_url_schemes": None,
            "requires_dist_url_policy": "ignore",
            "yanked_wheel_policy": "skip",
            "prerelease_policy": "default",
            "invalid_requires_dist_policy": "skip",
        },
        None,
        ["ignore", "skip", "default", "skip"],
        [
            "C006M002B0001",
            "C006M002B0004",
            "C006M002B0006",
            "C006M002B0008",
            "C006M002B0010",
            "C006M002B0012",
        ],
    ),
    # Covers: C006M002B0002, C006M002B0004, C006M002B0006, C006M002B0008, C006M002B0010, C006M002B0012
    (
        {
            "allowed_requires_dist_url_schemes": [],
            "requires_dist_url_policy": "honor",
            "yanked_wheel_policy": "allow",
            "prerelease_policy": "allow",
            "invalid_requires_dist_policy": "raise",
        },
        frozenset(),
        ["honor", "allow", "allow", "raise"],
        [
            "C006M002B0002",
            "C006M002B0004",
            "C006M002B0006",
            "C006M002B0008",
            "C006M002B0010",
            "C006M002B0012",
        ],
    ),
    # Covers: C006M002B0003, C006M002B0004, C006M002B0006, C006M002B0008, C006M002B0010, C006M002B0012
    (
        {
            "allowed_requires_dist_url_schemes": ["http", "https"],
            "requires_dist_url_policy": "raise",
            "yanked_wheel_policy": "skip",
            "prerelease_policy": "disallow",
            "invalid_requires_dist_policy": "skip",
        },
        frozenset({"http", "https"}),
        ["raise", "skip", "disallow", "skip"],
        [
            "C006M002B0003",
            "C006M002B0004",
            "C006M002B0006",
            "C006M002B0008",
            "C006M002B0010",
            "C006M002B0012",
        ],
    ),
]

POLICY_FROM_MAPPING_INVALID_ENUM_CASES = [
    # Covers: C006M002B0005
    (
        {
            "requires_dist_url_policy": "bogus",
            "yanked_wheel_policy": "skip",
            "prerelease_policy": "default",
            "invalid_requires_dist_policy": "skip",
        },
        "RequiresDistUrlPolicy",
        ["C006M002B0005"],
    ),
    # Covers: C006M002B0007
    (
        {
            "requires_dist_url_policy": "ignore",
            "yanked_wheel_policy": "bogus",
            "prerelease_policy": "default",
            "invalid_requires_dist_policy": "skip",
        },
        "YankedWheelPolicy",
        ["C006M002B0007"],
    ),
    # Covers: C006M002B0009
    (
        {
            "requires_dist_url_policy": "ignore",
            "yanked_wheel_policy": "skip",
            "prerelease_policy": "bogus",
            "invalid_requires_dist_policy": "skip",
        },
        "PreReleasePolicy",
        ["C006M002B0009"],
    ),
    # Covers: C006M002B0011
    (
        {
            "requires_dist_url_policy": "ignore",
            "yanked_wheel_policy": "skip",
            "prerelease_policy": "default",
            "invalid_requires_dist_policy": "bogus",
        },
        "InvalidRequiresDistPolicy",
        ["C006M002B0011"],
    ),
]

WHEEL_SPEC_POST_INIT_CASES = [
    # Covers: C008M001B0001, C008M001B0005
    (
        {
            "name": "pkg",
            "version": None,
            "extras": frozenset(),
            "marker": None,
            "uri": "  https://x  ",
        },
        "https://x",
        None,
        ["C008M001B0001", "C008M001B0005"],
    ),
    # Covers: C008M001B0002, C008M001B0005
    (
        {
            "name": "pkg",
            "version": ">=1",
            "extras": frozenset(),
            "marker": None,
            "uri": "   ",
        },
        None,
        ">=1",
        ["C008M001B0002", "C008M001B0005"],
    ),
    # Covers: C008M001B0003, C008M001B0005
    (
        {
            "name": "pkg",
            "version": ">=2",
            "extras": frozenset(),
            "marker": None,
            "uri": None,
        },
        None,
        ">=2",
        ["C008M001B0003", "C008M001B0005"],
    ),
]

WHEEL_SPEC_POST_INIT_RAISE_CASES = [
    # Covers: C008M001B0003, C008M001B0004
    (
        {
            "name": "pkg",
            "version": None,
            "extras": frozenset(),
            "marker": None,
            "uri": None,
        },
        "Must specify either a version or a URI",
        ["C008M001B0003", "C008M001B0004"],
    ),
]

WHEEL_SPEC_TO_MAPPING_CASES = [
    # Covers: C008M004B0001, C008M004B0004, C008M004B0005
    (
        WheelSpec(
            name="pkg",
            version=SpecifierSet(">=1"),
            extras=frozenset({"x"}),
            marker=None,
            uri="https://x",
        ),
        {"version": ">=1", "marker": None},
        ["C008M004B0001", "C008M004B0004", "C008M004B0005"],
    ),
    # Covers: C008M004B0001, C008M004B0003, C008M004B0005
    (
        WheelSpec(
            name="pkg",
            version=SpecifierSet(">=2"),
            extras=frozenset(),
            marker=Marker('python_version >= "3.11"'),
            uri=None,
        ),
        {"version": ">=2", "marker": 'python_version >= "3.11"'},
        ["C008M004B0001", "C008M004B0003", "C008M004B0005"],
    ),
]

WHEEL_SPEC_FROM_MAPPING_CASES = [
    # Covers: C008M005B0001, C008M005B0004, C008M005B0005
    (
        {
            "name": "pkg",
            "version": ">=1",
            "extras": [],
            "marker": None,
            "uri": "https://x",
        },
        (">=1", None, "https://x"),
        ["C008M005B0001", "C008M005B0004", "C008M005B0005"],
    ),
    # Covers: C008M005B0002, C008M005B0003, C008M005B0005
    # NOTE: uri must be non-empty here or WheelSpec.__post_init__ will raise.
    (
        {
            "name": "pkg",
            "version": None,
            "extras": ["a"],
            "marker": 'python_version >= "3.10"',
            "uri": "https://example.invalid/pkg.whl",
        },
        (None, 'python_version >= "3.10"', "https://example.invalid/pkg.whl"),
        ["C008M005B0002", "C008M005B0003", "C008M005B0005"],
    ),
]


# ==============================================================================
# Helpers
# ==============================================================================


@dataclass(frozen=True)
class _FakeKey:
    kind: Any = "WHEEL"  # not used by ResolutionError; present to resemble a key object


# ==============================================================================
# Tests
# ==============================================================================


@pytest.mark.parametrize("policy, expected_schemes, covers", POLICY_TO_MAPPING_CASES)
def test_resolution_policy_to_mapping_cases(
    policy: ResolutionPolicy,
    expected_schemes: list[str] | None,
    covers: list[str],
) -> None:
    # Covers (per-row): see POLICY_TO_MAPPING_CASES
    out = policy.to_mapping()

    assert out["requires_dist_url_policy"] == policy.requires_dist_url_policy.value
    assert out["yanked_wheel_policy"] == policy.yanked_wheel_policy.value
    assert out["prerelease_policy"] == policy.prerelease_policy.value
    assert (
        out["invalid_requires_dist_policy"] == policy.invalid_requires_dist_policy.value
    )

    assert out["allowed_requires_dist_url_schemes"] == expected_schemes


@pytest.mark.parametrize(
    "mapping, expected_allowed, expected_values, covers",
    POLICY_FROM_MAPPING_SUCCESS_CASES,
)
def test_resolution_policy_from_mapping_success_cases(
    mapping: Mapping[str, Any],
    expected_allowed: frozenset[str] | None,
    expected_values: list[str],
    covers: list[str],
) -> None:
    # Covers (per-row): see POLICY_FROM_MAPPING_SUCCESS_CASES
    p = ResolutionPolicy.from_mapping(mapping)

    assert p.allowed_requires_dist_url_schemes == expected_allowed
    assert p.requires_dist_url_policy.value == expected_values[0]
    assert p.yanked_wheel_policy.value == expected_values[1]
    assert p.prerelease_policy.value == expected_values[2]
    assert p.invalid_requires_dist_policy.value == expected_values[3]


@pytest.mark.parametrize(
    "mapping, expected_substring, covers", POLICY_FROM_MAPPING_INVALID_ENUM_CASES
)
def test_resolution_policy_from_mapping_invalid_enum_cases(
    mapping: Mapping[str, Any],
    expected_substring: str,
    covers: list[str],
) -> None:
    # Covers (per-row): see POLICY_FROM_MAPPING_INVALID_ENUM_CASES
    with pytest.raises(ValueError) as exc:
        ResolutionPolicy.from_mapping(mapping)

    assert expected_substring in str(exc.value)


# noinspection PyTypeChecker
def test_resolution_env_to_mapping_roundtrip_includes_policy_mapping() -> None:
    # Covers: C007M001B0001
    env = ResolutionEnv(
        identifier="env1",
        supported_tags=frozenset({"tag1", "tag2"}),
        marker_environment={},
        policy=ResolutionPolicy(
            allowed_requires_dist_url_schemes=None,
            requires_dist_url_policy=RequiresDistUrlPolicy.IGNORE,
            yanked_wheel_policy=YankedWheelPolicy.SKIP,
            prerelease_policy=PreReleasePolicy.DEFAULT,
            invalid_requires_dist_policy=InvalidRequiresDistPolicy.SKIP,
        ),
    )

    out = env.to_mapping()
    assert out["identifier"] == "env1"
    assert set(out["supported_tags"]) == {"tag1", "tag2"}
    assert out["marker_environment"] == {}
    assert isinstance(out["policy"], Mapping)
    assert (
        out["policy"]["requires_dist_url_policy"] == RequiresDistUrlPolicy.IGNORE.value
    )


def test_resolution_env_from_mapping_calls_validate_typed_dict_and_returns_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Covers: C007M002B0001, C007M002B0002
    calls: list[tuple[Any, ...]] = []

    def _fake_validate(
        desc: str, mapping: Mapping[str, Any], validation_type: type, value_type: Any
    ) -> None:
        calls.append((desc, dict(mapping), validation_type, value_type))

    monkeypatch.setattr(resolution, "validate_typed_dict", _fake_validate)

    env_map = {"os_name": "posix"}  # validator is stubbed at call site
    m = {
        "identifier": "env1",
        "supported_tags": ["tag1"],
        "marker_environment": env_map,
        # omit policy to force default policy_map path (still within unit)
    }

    env = ResolutionEnv.from_mapping(m)

    assert calls, "validate_typed_dict was not called"
    desc, seen_env_map, _validation_type, value_type = calls[0]
    assert desc == "marker_environment"
    assert seen_env_map == env_map
    assert value_type is str

    assert env.identifier == "env1"
    assert env.supported_tags == frozenset({"tag1"})
    assert env.marker_environment == env_map
    assert isinstance(env.policy, ResolutionPolicy)


@pytest.mark.parametrize(
    "kwargs, expected_uri, expected_version_str, covers", WHEEL_SPEC_POST_INIT_CASES
)
def test_wheel_spec_post_init_cases(
    kwargs: Mapping[str, Any],
    expected_uri: str | None,
    expected_version_str: str | None,
    covers: list[str],
) -> None:
    # Covers (per-row): see WHEEL_SPEC_POST_INIT_CASES
    version = SpecifierSet(kwargs["version"]) if kwargs["version"] is not None else None
    ws = WheelSpec(
        name=str(kwargs["name"]),
        version=version,
        extras=kwargs["extras"],
        marker=kwargs["marker"],
        uri=kwargs["uri"],
    )

    assert ws.uri == expected_uri
    if expected_version_str is None:
        assert ws.version is None
    else:
        assert str(ws.version) == expected_version_str


@pytest.mark.parametrize(
    "kwargs, expected_substring, covers", WHEEL_SPEC_POST_INIT_RAISE_CASES
)
def test_wheel_spec_post_init_raises(
    kwargs: Mapping[str, Any], expected_substring: str, covers: list[str]
) -> None:
    # Covers (per-row): see WHEEL_SPEC_POST_INIT_RAISE_CASES
    with pytest.raises(ValueError) as exc:
        WheelSpec(
            name=str(kwargs["name"]),
            version=None,
            extras=kwargs["extras"],
            marker=kwargs["marker"],
            uri=kwargs["uri"],
        )

    assert expected_substring in str(exc.value)


def test_wheel_spec_identifier_and_str_use_name_and_version() -> None:
    # Covers: C008M002B0001, C008M003B0001
    ws = WheelSpec(
        name="pkg",
        version=SpecifierSet(">=1"),
        extras=frozenset(),
        marker=None,
        uri=None,
    )
    assert ws.identifier == "pkg->=1"
    assert str(ws) == "pkg->=1"


@pytest.mark.parametrize("ws, expected_parts, covers", WHEEL_SPEC_TO_MAPPING_CASES)
def test_wheel_spec_to_mapping_cases(
    ws: WheelSpec,
    expected_parts: Mapping[str, Any],
    covers: list[str],
) -> None:
    # Covers (per-row): see WHEEL_SPEC_TO_MAPPING_CASES
    out = ws.to_mapping()

    assert out["name"] == "pkg"
    assert out["version"] == expected_parts["version"]
    assert out["marker"] == expected_parts["marker"]
    assert isinstance(out["extras"], list)
    assert out["uri"] == ws.uri


@pytest.mark.parametrize("mapping, expected, covers", WHEEL_SPEC_FROM_MAPPING_CASES)
def test_wheel_spec_from_mapping_cases(
    mapping: Mapping[str, Any],
    expected: tuple[str | None, str | None, str | None],
    covers: list[str],
) -> None:
    # Covers (per-row): see WHEEL_SPEC_FROM_MAPPING_CASES
    ws = WheelSpec.from_mapping(mapping)

    exp_version_str, exp_marker_str, exp_uri = expected
    if exp_version_str is None:
        assert ws.version is None
    else:
        assert str(ws.version) == exp_version_str

    if exp_marker_str is None:
        assert ws.marker is None
    else:
        assert str(ws.marker) == exp_marker_str

    assert ws.uri == exp_uri


# noinspection PyTypeChecker
def test_artifact_resolution_error_sets_key_causes_and_message() -> None:
    # Covers: C012M001B0001, C012M001B0002, C012M001B0003
    key = _FakeKey()
    causes = (RuntimeError("a"), ValueError("b"))

    err = ArtifactResolutionError("nope", key=key, causes=causes)

    assert str(err) == "nope"
    assert err.key is key
    assert err.causes == causes
