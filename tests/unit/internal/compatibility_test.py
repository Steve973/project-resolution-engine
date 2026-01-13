from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

import pytest


# NOTE: In-repo this should import from the real package path. The fallback keeps
# this test module runnable in isolated contexts.
try:  # pragma: no cover
    import project_resolution_engine.internal.compatibility as compat
except Exception:  # pragma: no cover
    # If the internal package import is unavailable (e.g., running this file in
    # an isolated sandbox), stub the multiformat mixin dependency so importing
    # the local `compatibility.py` works.
    import sys
    import types

    # Ensure parent packages exist for dotted-path imports.
    sys.modules.setdefault("project_resolution_engine", types.ModuleType("project_resolution_engine"))
    sys.modules.setdefault(
        "project_resolution_engine.internal", types.ModuleType("project_resolution_engine.internal")
    )
    sys.modules.setdefault(
        "project_resolution_engine.internal.util", types.ModuleType("project_resolution_engine.internal.util")
    )

    if "project_resolution_engine.internal.util.multiformat" not in sys.modules:
        multiformat_mod = types.ModuleType("project_resolution_engine.internal.util.multiformat")

        class MultiformatModelMixin:  # noqa: D401
            """Minimal stub for isolated test execution."""

        multiformat_mod.MultiformatModelMixin = MultiformatModelMixin
        sys.modules["project_resolution_engine.internal.util.multiformat"] = multiformat_mod

    import compatibility as compat  # type: ignore[no-redef]


# ==============================================================================
# BRANCH LEDGER: compatibility (C000)
# ==============================================================================
#
# Classes (in file order)
#   C001 = MarkerModeType
#   C002 = EnvironmentOverrides
#   C003 = MarkerEnvConfig
#   C004 = Filter
#   C005 = VersionSpec
#   C006 = InterpreterConfig
#   C007 = AbiConfig
#   C008 = PlatformVariant
#   C009 = PlatformConfig
#   C010 = PlatformContext
#   C011 = PlatformOverrides
#   C012 = ResolutionContext
#
# ------------------------------------------------------------------------------
# ## validate_typed_dict(desc, mapping, validation_type, value_type)
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: if bad_keys -> raises ValueError("Invalid {desc} keys: {bad_keys}")
# C000F001B0002: else (no bad_keys) -> continues to value validation
# C000F001B0003: if bad_vals -> raises ValueError("Invalid {desc} values: expected ...; ...")
# C000F001B0004: if bad_vals and isinstance(value_type, type) -> error message includes expected=value_type.__name__
# C000F001B0005: if bad_vals and else (value_type is tuple[type, ...]) -> error message includes expected=" | ".join(t.__name__ for t in value_type)
# C000F001B0006: else (no bad_vals) -> returns None
#
# ------------------------------------------------------------------------------
# ## MarkerEnvConfig.to_mapping(self)
#    (Class ID: C003, Method ID: M001)
# ------------------------------------------------------------------------------
# C003M001B0001: always -> returns {"overrides": self.overrides, "mode": self.mode.value}
#
# ------------------------------------------------------------------------------
# ## MarkerEnvConfig.from_mapping(cls, mapping, **_)
#    (Class ID: C003, Method ID: M002)
# ------------------------------------------------------------------------------
# C003M002B0001: if not isinstance(overrides, dict) -> raises ValueError("Invalid overrides value: expected dict; got ...")
# C003M002B0002: else (overrides is dict) -> calls validate_typed_dict("marker_env overrides", overrides_map, EnvironmentOverrides, str)
# C003M002B0003: MarkerModeType(mapping.get("mode", MarkerModeType.MERGE.value)) is valid -> returns MarkerEnvConfig(overrides=..., mode=...)
# C003M002B0004: MarkerModeType(mapping.get("mode", ...)) is invalid -> raises ValueError (enum conversion)
#
# ------------------------------------------------------------------------------
# ## Filter.to_mapping(self)
#    (Class ID: C004, Method ID: M001)
# ------------------------------------------------------------------------------
# C004M001B0001: always -> returns {"include": self.include, "exclude": self.exclude, "specific_only": self.specific_only}
#
# ------------------------------------------------------------------------------
# ## Filter.from_mapping(cls, mapping, **_)
#    (Class ID: C004, Method ID: M002)
# ------------------------------------------------------------------------------
# C004M002B0001: always -> returns Filter(include=mapping.get("include", []), exclude=mapping.get("exclude", []), specific_only=mapping.get("specific_only", False))
#
# ------------------------------------------------------------------------------
# ## VersionSpec.to_mapping(self)
#    (Class ID: C005, Method ID: M001)
# ------------------------------------------------------------------------------
# C005M001B0001: if self.range is not None -> result includes "range": self.range
# C005M001B0002: else (self.range is None) -> result does not include "range"
# C005M001B0003: if self.filters is not None -> result includes "filters": self.filters.to_mapping()
# C005M001B0004: else (self.filters is None) -> result does not include "filters"
# C005M001B0005: always -> returns result dict (possibly empty)
#
# ------------------------------------------------------------------------------
# ## VersionSpec.from_mapping(cls, mapping, **_)
#    (Class ID: C005, Method ID: M002)
# ------------------------------------------------------------------------------
# C005M002B0001: if filters_data -> filters = Filter.from_mapping(filters_data)
# C005M002B0002: else (no filters_data / falsy) -> filters = None
# C005M002B0003: always -> returns VersionSpec(range=mapping.get("range"), filters=filters)
#
# ------------------------------------------------------------------------------
# ## InterpreterConfig.to_mapping(self)
#    (Class ID: C006, Method ID: M001)
# ------------------------------------------------------------------------------
# C006M001B0001: if self.filters is not None -> result includes "filters": self.filters.to_mapping()
# C006M001B0002: else (self.filters is None) -> result does not include "filters"
# C006M001B0003: always -> returns dict with python_version/types/accept_universal (and maybe filters)
#
# ------------------------------------------------------------------------------
# ## InterpreterConfig.from_mapping(cls, mapping, **_)
#    (Class ID: C006, Method ID: M002)
# ------------------------------------------------------------------------------
# C006M002B0001: if filters_data -> filters = Filter.from_mapping(filters_data)
# C006M002B0002: else (no filters_data / falsy) -> filters = None
# C006M002B0003: if "python_version" missing -> raises KeyError
# C006M002B0004: else ("python_version" present) -> returns InterpreterConfig(python_version=VersionSpec.from_mapping(mapping["python_version"]), types=mapping.get("types", ["cp"]), accept_universal=mapping.get("accept_universal", True), filters=filters)
#
# ------------------------------------------------------------------------------
# ## AbiConfig.to_mapping(self)
#    (Class ID: C007, Method ID: M001)
# ------------------------------------------------------------------------------
# C007M001B0001: if self.filters is not None -> result includes "filters": self.filters.to_mapping()
# C007M001B0002: else (self.filters is None) -> result does not include "filters"
# C007M001B0003: always -> returns dict with include_debug/include_stable (and maybe filters)
#
# ------------------------------------------------------------------------------
# ## AbiConfig.from_mapping(cls, mapping, **_)
#    (Class ID: C007, Method ID: M002)
# ------------------------------------------------------------------------------
# C007M002B0001: if filters_data -> filters = Filter.from_mapping(filters_data)
# C007M002B0002: else (no filters_data / falsy) -> filters = None
# C007M002B0003: always -> returns AbiConfig(include_debug=mapping.get("include_debug", False), include_stable=mapping.get("include_stable", True), filters=filters)
#
# ------------------------------------------------------------------------------
# ## PlatformVariant.to_mapping(self)
#    (Class ID: C008, Method ID: M001)
# ------------------------------------------------------------------------------
# C008M001B0001: if self.version is not None -> result includes "version": self.version.to_mapping()
# C008M001B0002: else (self.version is None) -> result does not include "version"
# C008M001B0003: always -> returns dict with enabled (and maybe version)
#
# ------------------------------------------------------------------------------
# ## PlatformVariant.from_mapping(cls, mapping, **_)
#    (Class ID: C008, Method ID: M002)
# ------------------------------------------------------------------------------
# C008M002B0001: if version_data -> version = VersionSpec.from_mapping(version_data)
# C008M002B0002: else (no version_data / falsy) -> version = None
# C008M002B0003: always -> returns PlatformVariant(enabled=mapping.get("enabled", True), version=version)
#
# ------------------------------------------------------------------------------
# ## PlatformConfig.to_mapping(self)
#    (Class ID: C009, Method ID: M001)
# ------------------------------------------------------------------------------
# C009M001B0001: comprehension over self.variants.items() executes 0 times -> "variants" is {}
# C009M001B0002: comprehension over self.variants.items() executes >= 1 times -> "variants" includes mapped entries
# C009M001B0003: if self.filters is not None -> result includes "filters": self.filters.to_mapping()
# C009M001B0004: else (self.filters is None) -> result does not include "filters"
# C009M001B0005: always -> returns dict with enabled/arches/variants (and maybe filters)
#
# ------------------------------------------------------------------------------
# ## PlatformConfig.from_mapping(cls, mapping, **_)
#    (Class ID: C009, Method ID: M002)
# ------------------------------------------------------------------------------
# C009M002B0001: if filters_data -> filters = Filter.from_mapping(filters_data)
# C009M002B0002: else (no filters_data / falsy) -> filters = None
# C009M002B0003: if variants_data has no .items() (not a mapping-like) -> raises AttributeError at variants_data.items()
# C009M002B0004: comprehension over variants_data.items() executes 0 times -> variants is {}
# C009M002B0005: comprehension over variants_data.items() executes >= 1 times -> variants includes PlatformVariant.from_mapping(...) per entry
# C009M002B0006: always (when no exception above) -> returns PlatformConfig(enabled=mapping.get("enabled", True), arches=mapping.get("arches", []), variants=variants, filters=filters)
#
# ------------------------------------------------------------------------------
# ## PlatformContext.to_mapping(self)
#    (Class ID: C010, Method ID: M001)
# ------------------------------------------------------------------------------
# C010M001B0001: if self.interpreter is not None -> result includes "interpreter": self.interpreter.to_mapping()
# C010M001B0002: else (self.interpreter is None) -> result does not include "interpreter"
# C010M001B0003: if self.abi is not None -> result includes "abi": self.abi.to_mapping()
# C010M001B0004: else (self.abi is None) -> result does not include "abi"
# C010M001B0005: if self.platform is not None -> result includes "platform": self.platform.to_mapping()
# C010M001B0006: else (self.platform is None) -> result does not include "platform"
# C010M001B0007: if self.compatibility_tags is not None -> result includes "compatibility_tags": self.compatibility_tags.to_mapping()
# C010M001B0008: else (self.compatibility_tags is None) -> result does not include "compatibility_tags"
# C010M001B0009: if self.marker_env is not None -> result includes "marker_env": self.marker_env.to_mapping()
# C010M001B0010: else (self.marker_env is None) -> result does not include "marker_env"
# C010M001B0011: always -> returns result dict (possibly empty)
#
# ------------------------------------------------------------------------------
# ## PlatformContext.from_mapping(cls, mapping, **_)
#    (Class ID: C010, Method ID: M002)
# ------------------------------------------------------------------------------
# C010M002B0001: if interpreter_data -> interpreter = InterpreterConfig.from_mapping(interpreter_data)
# C010M002B0002: else (no interpreter_data / falsy) -> interpreter = None
# C010M002B0003: if abi_data -> abi = AbiConfig.from_mapping(abi_data)
# C010M002B0004: else (no abi_data / falsy) -> abi = None
# C010M002B0005: if platform_data -> platform = PlatformConfig.from_mapping(platform_data)
# C010M002B0006: else (no platform_data / falsy) -> platform = None
# C010M002B0007: if tags_data -> compatibility_tags = Filter.from_mapping(tags_data)
# C010M002B0008: else (no tags_data / falsy) -> compatibility_tags = None
# C010M002B0009: if marker_env_data -> marker_env = MarkerEnvConfig.from_mapping(marker_env_data)
# C010M002B0010: else (no marker_env_data / falsy) -> marker_env = None
# C010M002B0011: always -> returns PlatformContext(interpreter=..., abi=..., platform=..., compatibility_tags=..., marker_env=...)
#
# ------------------------------------------------------------------------------
# ## ResolutionContext.to_mapping(self)
#    (Class ID: C012, Method ID: M001)
# ------------------------------------------------------------------------------
# C012M001B0001: if self.platform_overrides -> out.update(platform_overrides={...}) is executed
# C012M001B0002: else (not self.platform_overrides) -> out does not include "platform_overrides"
# C012M001B0003: comprehension over self.platform_overrides.items() executes >= 1 times (only reachable when platform_overrides is truthy) -> platform_overrides mapping contains entries
# C012M001B0004: always -> returns out with "name" and "universal" (and maybe platform_overrides)
#
# ------------------------------------------------------------------------------
# ## ResolutionContext.from_mapping(cls, mapping, **_)
#    (Class ID: C012, Method ID: M002)
# ------------------------------------------------------------------------------
# C012M002B0001: if not isinstance(raw, Mapping) -> raises ValueError("platform_overrides must be a mapping")
# C012M002B0002: else (raw is a Mapping) -> continues parsing loop
# C012M002B0003: for platform_name, value in raw.items() executes 0 times -> parsed remains {}
# C012M002B0004: for platform_name, value in raw.items() executes >= 1 times -> enters loop body
# C012M002B0005: if value is None -> continue (entry skipped; parsed not updated for that platform)
# C012M002B0006: else (value is not None) -> continues type check
# C012M002B0007: if not isinstance(value, Mapping) -> raises ValueError(f"platform_overrides.{platform_name} must be a mapping")
# C012M002B0008: else (value is a Mapping) -> parsed[platform_name] = PlatformContext.from_mapping(value)
# C012M002B0009: validate_typed_dict("platform overrides", parsed, PlatformOverrides, PlatformContext) raises -> propagates ValueError from validate_typed_dict
# C012M002B0010: validate_typed_dict(...) succeeds -> returns ResolutionContext(name=mapping["name"], universal=PlatformContext.from_mapping(mapping["universal"]), platform_overrides=...)
# C012M002B0011: if "name" missing -> raises KeyError
# C012M002B0012: if "universal" missing -> raises KeyError
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none in this module)
#   [x] all `except` handlers captured (none in this module)
#   [x] all early `return`s / `raise`s / `yield`s captured
#   [x] all loop 0 vs >= 1 iterations captured (for-loops and comprehensions)
#   [x] all `break` / `continue` paths captured
# ==============================================================================


# ==============================
# 7) CASE MATRIX (per contract)
# ==============================


class _TD(TypedDict, total=False):
    ok: str


_VALIDATE_CASES: list[dict[str, Any]] = [
    {
        "id": "bad_keys",
        "desc": "td",
        "mapping": {"nope": "x"},
        "validation_type": _TD,
        "value_type": str,
        "exc_type": ValueError,
        "exc_sub": "Invalid td keys",
        "covers": ["C000F001B0001"],
    },
    {
        "id": "bad_vals_single_type",
        "desc": "td",
        "mapping": {"ok": 123},
        "validation_type": _TD,
        "value_type": str,
        "exc_type": ValueError,
        "exc_sub": "expected str",
        "covers": ["C000F001B0002", "C000F001B0003", "C000F001B0004"],
    },
    {
        "id": "bad_vals_tuple_type",
        "desc": "td",
        "mapping": {"ok": object()},
        "validation_type": _TD,
        "value_type": (int, str),
        "exc_type": ValueError,
        "exc_sub": "expected int | str",
        "covers": ["C000F001B0002", "C000F001B0003", "C000F001B0005"],
    },
    {
        "id": "ok",
        "desc": "td",
        "mapping": {"ok": "x"},
        "validation_type": _TD,
        "value_type": str,
        "exc_type": None,
        "exc_sub": None,
        "covers": ["C000F001B0002", "C000F001B0006"],
    },
]


_MARKER_ENV_FROM_MAPPING_CASES: list[dict[str, Any]] = [
    {
        "id": "overrides_not_dict",
        "mapping": {"overrides": ["nope"]},
        "exc_type": ValueError,
        "exc_sub": "Invalid overrides value: expected dict",
        "covers": ["C003M002B0001"],
    },
    {
        "id": "overrides_bad_key",
        "mapping": {"overrides": {"nope": "x"}},
        "exc_type": ValueError,
        "exc_sub": "Invalid marker_env overrides keys",
        "covers": ["C003M002B0002", "C000F001B0001"],
    },
    {
        "id": "overrides_bad_value_type",
        "mapping": {"overrides": {"python_version": 123}},
        "exc_type": ValueError,
        "exc_sub": "Invalid marker_env overrides values: expected str",
        "covers": ["C003M002B0002", "C000F001B0003", "C000F001B0004"],
    },
    {
        "id": "invalid_mode",
        "mapping": {"overrides": {}, "mode": "nope"},
        "exc_type": ValueError,
        "exc_sub": "MarkerModeType",
        "covers": ["C003M002B0004"],
    },
    {
        "id": "ok_defaults",
        "mapping": {"overrides": {"python_version": "3.12"}},
        "exc_type": None,
        "exc_sub": None,
        "covers": ["C003M002B0002", "C003M002B0003"],
    },
]


# ==============================
# 8) TESTS
# ==============================


@pytest.mark.parametrize("case", _VALIDATE_CASES, ids=[c["id"] for c in _VALIDATE_CASES])
def test_validate_typed_dict(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    if case["exc_type"] is None:
        assert (
            compat.validate_typed_dict(
                case["desc"],
                case["mapping"],
                case["validation_type"],
                case["value_type"],
            )
            is None
        )
        return

    with pytest.raises(case["exc_type"]) as excinfo:
        compat.validate_typed_dict(
            case["desc"],
            case["mapping"],
            case["validation_type"],
            case["value_type"],
        )

    assert case["exc_sub"] in str(excinfo.value)


@pytest.mark.parametrize(
    "case", _MARKER_ENV_FROM_MAPPING_CASES, ids=[c["id"] for c in _MARKER_ENV_FROM_MAPPING_CASES]
)
def test_marker_env_config_from_mapping(case: dict[str, Any]) -> None:
    # Covers: see case["covers"]
    if case["exc_type"] is None:
        cfg = compat.MarkerEnvConfig.from_mapping(case["mapping"])
        assert isinstance(cfg.overrides, dict)
        assert cfg.overrides.get("python_version") == "3.12"
        assert cfg.mode == compat.MarkerModeType.MERGE
        return

    with pytest.raises(case["exc_type"]) as excinfo:
        compat.MarkerEnvConfig.from_mapping(case["mapping"])

    assert case["exc_sub"] in str(excinfo.value)


def test_marker_env_config_to_mapping() -> None:
    # Covers: C003M001B0001
    cfg = compat.MarkerEnvConfig(overrides={"python_version": "3.11"}, mode=compat.MarkerModeType.EXACT)
    out = cfg.to_mapping()
    assert out["overrides"] == {"python_version": "3.11"}
    assert out["mode"] == "exact"


def test_filter_to_from_mapping_roundtrip() -> None:
    # Covers: C004M001B0001, C004M002B0001
    f = compat.Filter(include=["a"], exclude=["b"], specific_only=True)
    mapped = f.to_mapping()
    assert mapped == {"include": ["a"], "exclude": ["b"], "specific_only": True}

    reread = compat.Filter.from_mapping({"include": ["x"], "exclude": ["y"], "specific_only": False})
    assert reread.include == ["x"]
    assert reread.exclude == ["y"]
    assert reread.specific_only is False

    defaults = compat.Filter.from_mapping({})
    assert defaults.include == []
    assert defaults.exclude == []
    assert defaults.specific_only is False


@pytest.mark.parametrize(
    "spec, expected, covers",
    [
        # range=None, filters=None
        (compat.VersionSpec(range=None, filters=None), {}, ["C005M001B0002", "C005M001B0004", "C005M001B0005"]),
        # range!=None, filters=None
        (
            compat.VersionSpec(range=">=3.10,<4", filters=None),
            {"range": ">=3.10,<4"},
            ["C005M001B0001", "C005M001B0004", "C005M001B0005"],
        ),
        # range=None, filters!=None
        (
            compat.VersionSpec(range=None, filters=compat.Filter(include=["x"])),
            {"filters": {"include": ["x"], "exclude": [], "specific_only": False}},
            ["C005M001B0002", "C005M001B0003", "C005M001B0005"],
        ),
        # range!=None, filters!=None
        (
            compat.VersionSpec(range=">=1", filters=compat.Filter(exclude=["y"])),
            {
                "range": ">=1",
                "filters": {"include": [], "exclude": ["y"], "specific_only": False},
            },
            ["C005M001B0001", "C005M001B0003", "C005M001B0005"],
        ),
    ],
    ids=["range_none_filters_none", "range_only", "filters_only", "range_and_filters"],
)
def test_version_spec_to_mapping(spec: compat.VersionSpec, expected: dict[str, Any], covers: list[str]) -> None:
    # Covers: see `covers`
    assert spec.to_mapping() == expected


@pytest.mark.parametrize(
    "mapping, expected_filters_is_none, covers",
    [
        ({"range": ">=3"}, True, ["C005M002B0002", "C005M002B0003"]),
        (
            {"range": ">=3", "filters": {"include": ["a"]}},
            False,
            ["C005M002B0001", "C005M002B0003"],
        ),
    ],
    ids=["no_filters", "with_filters"],
)
def test_version_spec_from_mapping(mapping: Mapping[str, Any], expected_filters_is_none: bool, covers: list[str]) -> None:
    # Covers: see `covers`
    spec = compat.VersionSpec.from_mapping(mapping)
    assert spec.range == mapping.get("range")
    assert (spec.filters is None) is expected_filters_is_none


def test_interpreter_config_to_mapping_filters_absent_and_present() -> None:
    # Covers: C006M001B0001, C006M001B0002, C006M001B0003
    base = compat.InterpreterConfig(python_version=compat.VersionSpec(range=">=3.10"), types=["cp"])
    out_base = base.to_mapping()
    assert "filters" not in out_base

    with_filters = compat.InterpreterConfig(
        python_version=compat.VersionSpec(range=">=3.10"),
        types=["cp"],
        accept_universal=False,
        filters=compat.Filter(include=["cp310"]),
    )
    out_filters = with_filters.to_mapping()
    assert out_filters["filters"]["include"] == ["cp310"]


@pytest.mark.parametrize(
    "mapping, exc_type, exc_sub, covers",
    [
        # missing python_version
        ({}, KeyError, "python_version", ["C006M002B0002", "C006M002B0003"]),
        # present python_version, no filters
        (
            {"python_version": {"range": ">=3.11"}},
            None,
            None,
            ["C006M002B0002", "C006M002B0004"],
        ),
        # present python_version, with filters
        (
            {
                "python_version": {"range": ">=3.11"},
                "filters": {"exclude": ["pp"]},
                "types": ["cp", "pp"],
                "accept_universal": False,
            },
            None,
            None,
            ["C006M002B0001", "C006M002B0004"],
        ),
    ],
    ids=["missing_python_version", "defaults_no_filters", "explicit_with_filters"],
)
def test_interpreter_config_from_mapping(
    mapping: Mapping[str, Any],
    exc_type: type[BaseException] | None,
    exc_sub: str | None,
    covers: list[str],
) -> None:
    # Covers: see `covers`
    if exc_type is not None:
        with pytest.raises(exc_type) as excinfo:
            compat.InterpreterConfig.from_mapping(mapping)
        assert exc_sub in str(excinfo.value)
        return

    cfg = compat.InterpreterConfig.from_mapping(mapping)
    assert isinstance(cfg.python_version, compat.VersionSpec)

    if "types" in mapping:
        assert cfg.types == list(mapping["types"])  # type: ignore[arg-type]
        assert cfg.accept_universal is False
        assert cfg.filters is not None
        assert cfg.filters.exclude == ["pp"]
    else:
        # defaults
        assert cfg.types == ["cp"]
        assert cfg.accept_universal is True
        assert cfg.filters is None


def test_abi_config_to_mapping_filters_absent_and_present() -> None:
    # Covers: C007M001B0001, C007M001B0002, C007M001B0003
    base = compat.AbiConfig()
    out_base = base.to_mapping()
    assert "filters" not in out_base

    with_filters = compat.AbiConfig(filters=compat.Filter(include=["abi3"]))
    out_filters = with_filters.to_mapping()
    assert out_filters["filters"]["include"] == ["abi3"]


@pytest.mark.parametrize(
    "mapping, expected_filters_is_none, covers",
    [
        ({}, True, ["C007M002B0002", "C007M002B0003"]),
        ({"filters": {"include": ["x"]}}, False, ["C007M002B0001", "C007M002B0003"]),
    ],
    ids=["no_filters", "with_filters"],
)
def test_abi_config_from_mapping(mapping: Mapping[str, Any], expected_filters_is_none: bool, covers: list[str]) -> None:
    # Covers: see `covers`
    cfg = compat.AbiConfig.from_mapping(mapping)
    assert (cfg.filters is None) is expected_filters_is_none


def test_platform_variant_to_mapping_version_absent_and_present() -> None:
    # Covers: C008M001B0001, C008M001B0002, C008M001B0003
    no_ver = compat.PlatformVariant(enabled=False, version=None)
    out_no_ver = no_ver.to_mapping()
    assert "version" not in out_no_ver

    with_ver = compat.PlatformVariant(enabled=True, version=compat.VersionSpec(range=">=1"))
    out_with_ver = with_ver.to_mapping()
    assert out_with_ver["version"] == {"range": ">=1"}


@pytest.mark.parametrize(
    "mapping, expected_version_is_none, covers",
    [
        ({}, True, ["C008M002B0002", "C008M002B0003"]),
        ({"version": {"range": ">=2"}}, False, ["C008M002B0001", "C008M002B0003"]),
    ],
    ids=["no_version", "with_version"],
)
def test_platform_variant_from_mapping(mapping: Mapping[str, Any], expected_version_is_none: bool, covers: list[str]) -> None:
    # Covers: see `covers`
    pv = compat.PlatformVariant.from_mapping(mapping)
    assert (pv.version is None) is expected_version_is_none


def test_platform_config_to_mapping_variants_0_and_1_and_filters() -> None:
    # Covers: C009M001B0001, C009M001B0002, C009M001B0003, C009M001B0004, C009M001B0005
    empty = compat.PlatformConfig(enabled=True, arches=["x86_64"], variants={}, filters=None)
    out_empty = empty.to_mapping()
    assert out_empty["variants"] == {}
    assert "filters" not in out_empty

    one = compat.PlatformConfig(
        enabled=False,
        arches=["aarch64"],
        variants={"manylinux": compat.PlatformVariant(enabled=True)},
        filters=compat.Filter(exclude=["musllinux"]),
    )
    out_one = one.to_mapping()
    assert out_one["variants"]["manylinux"] == {"enabled": True}
    assert out_one["filters"]["exclude"] == ["musllinux"]


@pytest.mark.parametrize(
    "mapping, exc_type, exc_sub, expected_variants_len, expected_filters_is_none, covers",
    [
        # variants_data has no .items()
        (
            {"variants": ["nope"]},
            AttributeError,
            "items",
            None,
            None,
            ["C009M002B0003"],
        ),
        # variants empty, no filters
        (
            {"variants": {}},
            None,
            None,
            0,
            True,
            ["C009M002B0002", "C009M002B0004", "C009M002B0006"],
        ),
        # variants non-empty, with filters
        (
            {
                "enabled": False,
                "arches": ["x86_64"],
                "variants": {"manylinux": {"enabled": False}},
                "filters": {"include": ["x86_64"]},
            },
            None,
            None,
            1,
            False,
            ["C009M002B0001", "C009M002B0005", "C009M002B0006"],
        ),
    ],
    ids=["variants_not_mapping", "variants_empty", "variants_nonempty_with_filters"],
)
def test_platform_config_from_mapping(
    mapping: Mapping[str, Any],
    exc_type: type[BaseException] | None,
    exc_sub: str | None,
    expected_variants_len: int | None,
    expected_filters_is_none: bool | None,
    covers: list[str],
) -> None:
    # Covers: see `covers`
    if exc_type is not None:
        with pytest.raises(exc_type) as excinfo:
            compat.PlatformConfig.from_mapping(mapping)
        assert exc_sub in str(excinfo.value)
        return

    cfg = compat.PlatformConfig.from_mapping(mapping)
    assert len(cfg.variants) == expected_variants_len
    assert (cfg.filters is None) is expected_filters_is_none


def test_platform_context_to_mapping_empty_and_all_fields() -> None:
    # Covers: C010M001B0001..B0011
    empty = compat.PlatformContext()
    out_empty = empty.to_mapping()
    assert out_empty == {}

    full = compat.PlatformContext(
        interpreter=compat.InterpreterConfig(python_version=compat.VersionSpec(range=">=3.11"), types=["cp"]),
        abi=compat.AbiConfig(include_debug=True, include_stable=False),
        platform=compat.PlatformConfig(arches=["x86_64"], variants={"manylinux": compat.PlatformVariant()}),
        compatibility_tags=compat.Filter(include=["cp311"]),
        marker_env=compat.MarkerEnvConfig(overrides={"python_version": "3.11"}),
    )
    out_full = full.to_mapping()
    assert set(out_full.keys()) == {"interpreter", "abi", "platform", "compatibility_tags", "marker_env"}


def test_platform_context_from_mapping_empty_and_all_fields() -> None:
    # Covers: C010M002B0001..B0011
    empty = compat.PlatformContext.from_mapping({})
    assert empty.interpreter is None
    assert empty.abi is None
    assert empty.platform is None
    assert empty.compatibility_tags is None
    assert empty.marker_env is None

    full = compat.PlatformContext.from_mapping(
        {
            "interpreter": {"python_version": {"range": ">=3.11"}},
            "abi": {"include_debug": True, "include_stable": False},
            "platform": {"arches": ["x86_64"], "variants": {"manylinux": {"enabled": True}}},
            "compatibility_tags": {"include": ["cp311"]},
            "marker_env": {"overrides": {"python_version": "3.11"}},
        }
    )
    assert isinstance(full.interpreter, compat.InterpreterConfig)
    assert isinstance(full.abi, compat.AbiConfig)
    assert isinstance(full.platform, compat.PlatformConfig)
    assert isinstance(full.compatibility_tags, compat.Filter)
    assert isinstance(full.marker_env, compat.MarkerEnvConfig)


def test_resolution_context_to_mapping_overrides_absent_and_present() -> None:
    # Covers: C012M001B0001, C012M001B0002, C012M001B0003, C012M001B0004
    rc_empty = compat.ResolutionContext(name="n", universal=compat.PlatformContext(), platform_overrides={})
    out_empty = rc_empty.to_mapping()
    assert "platform_overrides" not in out_empty

    rc_one = compat.ResolutionContext(
        name="n",
        universal=compat.PlatformContext(),
        platform_overrides={"linux": compat.PlatformContext(platform=compat.PlatformConfig(arches=["x86_64"]))},
    )
    out_one = rc_one.to_mapping()
    assert out_one["platform_overrides"]["linux"]["platform"]["arches"] == ["x86_64"]


@pytest.mark.parametrize(
    "mapping, exc_type, exc_sub, expected_overrides_keys, covers",
    [
        (
            {"name": "n", "universal": {}, "platform_overrides": []},
            ValueError,
            "platform_overrides must be a mapping",
            None,
            ["C012M002B0001"],
        ),
        (
            {"name": "n", "universal": {}, "platform_overrides": {}},
            None,
            None,
            [],
            ["C012M002B0002", "C012M002B0003", "C012M002B0010"],
        ),
        (
            {"name": "n", "universal": {}, "platform_overrides": {"linux": None}},
            None,
            None,
            [],
            ["C012M002B0004", "C012M002B0005", "C012M002B0010"],
        ),
        (
            {"name": "n", "universal": {}, "platform_overrides": {"linux": 123}},
            ValueError,
            "platform_overrides.linux must be a mapping",
            None,
            ["C012M002B0004", "C012M002B0006", "C012M002B0007"],
        ),
        (
            {"name": "n", "universal": {}, "platform_overrides": {"weird": {}}},
            ValueError,
            "Invalid platform overrides keys",
            None,
            ["C012M002B0004", "C012M002B0008", "C012M002B0009"],
        ),
        (
            {"name": "n", "universal": {}, "platform_overrides": {"linux": {}}},
            None,
            None,
            ["linux"],
            ["C012M002B0004", "C012M002B0008", "C012M002B0010"],
        ),
        (
            {"universal": {}, "platform_overrides": {}},
            KeyError,
            "name",
            None,
            ["C012M002B0011"],
        ),
        (
            {"name": "n", "platform_overrides": {}},
            KeyError,
            "universal",
            None,
            ["C012M002B0012"],
        ),
    ],
    ids=[
        "raw_not_mapping",
        "raw_empty_mapping",
        "raw_one_none_skipped",
        "raw_value_not_mapping",
        "validate_typed_dict_invalid_key",
        "success_one_override",
        "missing_name",
        "missing_universal",
    ],
)
def test_resolution_context_from_mapping(
    mapping: Mapping[str, Any],
    exc_type: type[BaseException] | None,
    exc_sub: str | None,
    expected_overrides_keys: list[str] | None,
    covers: list[str],
) -> None:
    # Covers: see `covers`
    if exc_type is not None:
        with pytest.raises(exc_type) as excinfo:
            compat.ResolutionContext.from_mapping(mapping)
        assert exc_sub in str(excinfo.value)
        return

    rc = compat.ResolutionContext.from_mapping(mapping)
    assert rc.name == "n"
    assert isinstance(rc.universal, compat.PlatformContext)

    keys = list(getattr(rc.platform_overrides, "keys")())  # TypedDict in runtime is just a dict
    assert sorted(keys) == sorted(expected_overrides_keys)
