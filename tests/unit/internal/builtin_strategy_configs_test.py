from __future__ import annotations

# ==============================================================================
# BRANCH LEDGER: builtin_strategy_configs (C000)
# ==============================================================================
#
# ------------------------------------------------------------------------------
# ## _unknown_keys(cfg, allowed, *, ctx)
#    (Module ID: C000, Function ID: F001)
# ------------------------------------------------------------------------------
# C000F001B0001: if extra -> raise StrategyConfigError (message contains f"{ctx}: unknown config keys:" and the unknown keys)
# C000F001B0002: else (not extra) -> return None
#
# ------------------------------------------------------------------------------
# ## _opt_str(cfg, key)
#    (Module ID: C000, Function ID: F002)
# ------------------------------------------------------------------------------
# C000F002B0001: if key not in cfg -> return None
# C000F002B0002: if key in cfg and isinstance(v, str) -> return v
# C000F002B0003: if key in cfg and not isinstance(v, str) -> raise StrategyConfigError (message contains f"{key}: expected str, got {type(v).__name__}")
#
# ------------------------------------------------------------------------------
# ## _opt_int(cfg, key)
#    (Module ID: C000, Function ID: F003)
# ------------------------------------------------------------------------------
# C000F003B0001: if key not in cfg -> return None
# C000F003B0002: if key in cfg and isinstance(v, int) -> return v
# C000F003B0003: if key in cfg and not isinstance(v, int) -> raise StrategyConfigError (message contains f"{key}: expected int, got {type(v).__name__}")
#
# ------------------------------------------------------------------------------
# ## _opt_float(cfg, key)
#    (Module ID: C000, Function ID: F004)
# ------------------------------------------------------------------------------
# C000F004B0001: if key not in cfg -> return None
# C000F004B0002: if key in cfg and isinstance(v, int) -> return float(v)
# C000F004B0003: if key in cfg and isinstance(v, float) -> return v
# C000F004B0004: if key in cfg and not isinstance(v, float) and not isinstance(v, int) -> raise StrategyConfigError (message contains f"{key}: expected float, got {type(v).__name__}")
#
# ------------------------------------------------------------------------------
# ## _plan_single(*, strategy_name, strategy_cls, config, ctor_kwargs, depends_on=())
#    (Module ID: C000, Function ID: F005)
# ------------------------------------------------------------------------------
# C000F005B0001: str(config.get("instance_id") or "") is truthy -> instance_id == that string
# C000F005B0002: str(config.get("instance_id") or "") is falsy -> instance_id == strategy_name
# C000F005B0003: "precedence" in config -> precedence == int(config.get("precedence", ...)) (i.e., int(config["precedence"]))
# C000F005B0004: "precedence" not in config -> precedence == int(getattr(strategy_cls, "precedence", 100))
# C000F005B0005: int(config.get("precedence", getattr(strategy_cls, "precedence", 100))) raises (TypeError/ValueError) -> exception propagates
# C000F005B0006: "instance_id" not in ctor_kwargs -> full_kwargs["instance_id"] set to computed instance_id
# C000F005B0007: "instance_id" in ctor_kwargs -> full_kwargs["instance_id"] remains ctor_kwargs["instance_id"]
# C000F005B0008: "precedence" not in ctor_kwargs -> full_kwargs["precedence"] set to computed precedence
# C000F005B0009: "precedence" in ctor_kwargs -> full_kwargs["precedence"] remains ctor_kwargs["precedence"]
# C000F005B0010: return [StrategyPlan(...)] -> returns list length 1; plan.instance_id==instance_id; plan.precedence==precedence; plan.depends_on==depends_on; plan.ctor_kwargs==full_kwargs
#
# ------------------------------------------------------------------------------
# ## Pep691IndexMetadataHttpStrategyConfig.defaults(cls)
#    (Class ID: C002, Method ID: M001)
# ------------------------------------------------------------------------------
# C002M001B0001: return mapping literal -> returns {"timeout_s": 30.0, "user_agent": "project-resolution-engine/0", "precedence": 50}
#
# ------------------------------------------------------------------------------
# ## Pep691IndexMetadataHttpStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C002, Method ID: M002)
# ------------------------------------------------------------------------------
# C002M002B0001: extra config keys beyond (_RESERVED_KEYS | {"timeout_s", "user_agent"}) -> raise StrategyConfigError (from _unknown_keys)
# C002M002B0002: no extra config keys -> continue (ctor starts as {})
# C002M002B0003: (v_timeout := _opt_float(config, "timeout_s")) is not None -> ctor["timeout_s"] set; returned plan.ctor_kwargs includes "timeout_s"
# C002M002B0004: (v_timeout := _opt_float(config, "timeout_s")) is None -> ctor has no "timeout_s"
# C002M002B0005: _opt_float(config, "timeout_s") raises StrategyConfigError -> exception propagates
# C002M002B0006: (v_agent := _opt_str(config, "user_agent")) is not None -> ctor["user_agent"] set; returned plan.ctor_kwargs includes "user_agent"
# C002M002B0007: (v_agent := _opt_str(config, "user_agent")) is None -> ctor has no "user_agent"
# C002M002B0008: _opt_str(config, "user_agent") raises StrategyConfigError -> exception propagates
# C002M002B0009: _plan_single(...) succeeds -> returns list length 1 with StrategyPlan.strategy_name == cls.strategy_name
# C002M002B0010: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# ## HttpWheelFileStrategyConfig.defaults(cls)
#    (Class ID: C003, Method ID: M001)
# ------------------------------------------------------------------------------
# C003M001B0001: return mapping literal -> returns {"timeout_s": 120.0, "user_agent": "project-resolution-engine/0", "chunk_bytes": 1024 * 1024, "precedence": 50}
#
# ------------------------------------------------------------------------------
# ## HttpWheelFileStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C003, Method ID: M002)
# ------------------------------------------------------------------------------
# C003M002B0001: extra config keys beyond (_RESERVED_KEYS | {"timeout_s", "user_agent", "chunk_bytes"}) -> raise StrategyConfigError (from _unknown_keys)
# C003M002B0002: no extra config keys -> continue (ctor starts as {})
# C003M002B0003: (v_timeout := _opt_float(config, "timeout_s")) is not None -> ctor["timeout_s"] set
# C003M002B0004: (v_timeout := _opt_float(config, "timeout_s")) is None -> ctor has no "timeout_s"
# C003M002B0005: _opt_float(config, "timeout_s") raises StrategyConfigError -> exception propagates
# C003M002B0006: (v_agent := _opt_str(config, "user_agent")) is not None -> ctor["user_agent"] set
# C003M002B0007: (v_agent := _opt_str(config, "user_agent")) is None -> ctor has no "user_agent"
# C003M002B0008: _opt_str(config, "user_agent") raises StrategyConfigError -> exception propagates
# C003M002B0009: (v_chunk_bytes := _opt_int(config, "chunk_bytes")) is not None -> ctor["chunk_bytes"] set
# C003M002B0010: (v_chunk_bytes := _opt_int(config, "chunk_bytes")) is None -> ctor has no "chunk_bytes"
# C003M002B0011: _opt_int(config, "chunk_bytes") raises StrategyConfigError -> exception propagates
# C003M002B0012: _plan_single(...) succeeds -> returns list length 1 with StrategyPlan.strategy_name == cls.strategy_name
# C003M002B0013: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# ## Pep658CoreMetadataHttpStrategyConfig.defaults(cls)
#    (Class ID: C004, Method ID: M001)
# ------------------------------------------------------------------------------
# C004M001B0001: return mapping literal -> returns {"timeout_s": 30.0, "user_agent": "project-resolution-engine/0", "precedence": 50}
#
# ------------------------------------------------------------------------------
# ## Pep658CoreMetadataHttpStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C004, Method ID: M002)
# ------------------------------------------------------------------------------
# C004M002B0001: extra config keys beyond (_RESERVED_KEYS | {"timeout_s", "user_agent"}) -> raise StrategyConfigError (from _unknown_keys)
# C004M002B0002: no extra config keys -> continue (ctor starts as {})
# C004M002B0003: (v_timeout := _opt_float(config, "timeout_s")) is not None -> ctor["timeout_s"] set
# C004M002B0004: (v_timeout := _opt_float(config, "timeout_s")) is None -> ctor has no "timeout_s"
# C004M002B0005: _opt_float(config, "timeout_s") raises StrategyConfigError -> exception propagates
# C004M002B0006: (v_agent := _opt_str(config, "user_agent")) is not None -> ctor["user_agent"] set
# C004M002B0007: (v_agent := _opt_str(config, "user_agent")) is None -> ctor has no "user_agent"
# C004M002B0008: _opt_str(config, "user_agent") raises StrategyConfigError -> exception propagates
# C004M002B0009: _plan_single(...) succeeds -> returns list length 1 with StrategyPlan.strategy_name == cls.strategy_name
# C004M002B0010: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# ## WheelExtractedCoreMetadataStrategyConfig.defaults(cls)
#    (Class ID: C005, Method ID: M001)
# ------------------------------------------------------------------------------
# C005M001B0001: return mapping literal -> returns {"wheel_strategy_id": "wheel_http", "wheel_timeout_s": 120.0, "precedence": 90}
#
# ------------------------------------------------------------------------------
# ## WheelExtractedCoreMetadataStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C005, Method ID: M002)
# ------------------------------------------------------------------------------
# C005M002B0001: extra config keys beyond (_RESERVED_KEYS | {"wheel_strategy_id", "wheel_timeout_s"}) -> raise StrategyConfigError (from _unknown_keys)
# C005M002B0002: no extra config keys -> continue
# C005M002B0003: _opt_str(config, "wheel_strategy_id") returns a truthy str -> wheel_sid == that value; wheel_ref uses that id
# C005M002B0004: _opt_str(config, "wheel_strategy_id") returns None or "" -> wheel_sid == "wheel_http"; wheel_ref uses "wheel_http"
# C005M002B0005: _opt_str(config, "wheel_strategy_id") raises StrategyConfigError -> exception propagates
# C005M002B0006: (v := _opt_float(config, "wheel_timeout_s")) is not None -> ctor["wheel_timeout_s"] set
# C005M002B0007: (v := _opt_float(config, "wheel_timeout_s")) is None -> ctor has no "wheel_timeout_s"
# C005M002B0008: _opt_float(config, "wheel_timeout_s") raises StrategyConfigError -> exception propagates
# C005M002B0009: _plan_single(..., depends_on=(wheel_ref.normalized_instance_id(),)) succeeds -> returns list length 1; plan.depends_on contains that single normalized id
# C005M002B0010: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# ## DirectUriWheelFileStrategyConfig.defaults(cls)
#    (Class ID: C006, Method ID: M001)
# ------------------------------------------------------------------------------
# C006M001B0001: return mapping literal -> returns {"chunk_bytes": 1024 * 1024, "precedence": 40}
#
# ------------------------------------------------------------------------------
# ## DirectUriWheelFileStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C006, Method ID: M002)
# ------------------------------------------------------------------------------
# C006M002B0001: extra config keys beyond (_RESERVED_KEYS | {"chunk_bytes"}) -> raise StrategyConfigError (from _unknown_keys)
# C006M002B0002: no extra config keys -> continue (ctor starts as {})
# C006M002B0003: (v := _opt_int(config, "chunk_bytes")) is not None -> ctor["chunk_bytes"] set
# C006M002B0004: (v := _opt_int(config, "chunk_bytes")) is None -> ctor has no "chunk_bytes"
# C006M002B0005: _opt_int(config, "chunk_bytes") raises StrategyConfigError -> exception propagates
# C006M002B0006: _plan_single(...) succeeds -> returns list length 1 with StrategyPlan.strategy_name == cls.strategy_name
# C006M002B0007: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# ## DirectUriCoreMetadataStrategyConfig.defaults(cls)
#    (Class ID: C007, Method ID: M001)
# ------------------------------------------------------------------------------
# C007M001B0001: return mapping literal -> returns {"precedence": 40}
#
# ------------------------------------------------------------------------------
# ## DirectUriCoreMetadataStrategyConfig.plan(cls, *, strategy_cls, config)
#    (Class ID: C007, Method ID: M002)
# ------------------------------------------------------------------------------
# C007M002B0001: extra config keys beyond _RESERVED_KEYS -> raise StrategyConfigError (from _unknown_keys)
# C007M002B0002: no extra config keys -> continue
# C007M002B0003: _plan_single(..., ctor_kwargs={}) succeeds -> returns list length 1 with empty ctor kwargs (except injected instance_id/precedence via _plan_single)
# C007M002B0004: _plan_single(...) raises (TypeError/ValueError from precedence int conversion) -> exception propagates
#
# ------------------------------------------------------------------------------
# LEDGER COMPLETENESS CHECKLIST
#   [x] all `if` / `elif` / `else` captured
#   [x] all `match` / `case` arms captured (none in this module)
#   [x] all `except` handlers captured (none in this module)
#   [x] all early `return`s / `raise`s / `yield`s captured
#   [x] all loop 0 vs >= 1 iterations captured (no loops in this module)
#   [x] all `break` / `continue` paths captured (no loops in this module)
# ==============================================================================

import pytest

from project_resolution_engine.internal import builtin_strategy_configs as uut


class _DummyStrategy:
    precedence = 777


# ---------------------------------------------------------------------------
# Case matrices (required by contract)
# ---------------------------------------------------------------------------

UNKNOWN_KEYS_CASES = [
    {
        "name": "no_extra",
        "cfg": {"a": 1},
        "allowed": {"a"},
        "ctx": "ctx",
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F001B0002"],
    },
    {
        "name": "extra_raises",
        "cfg": {"a": 1, "b": 2},
        "allowed": {"a"},
        "ctx": "pep691_http",
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "pep691_http: unknown config keys",
        "covers": ["C000F001B0001"],
    },
]

OPT_STR_CASES = [
    {
        "name": "missing",
        "cfg": {},
        "key": "user_agent",
        "expect": None,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F002B0001"],
    },
    {
        "name": "present_str",
        "cfg": {"user_agent": "ua"},
        "key": "user_agent",
        "expect": "ua",
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F002B0002"],
    },
    {
        "name": "present_wrong_type",
        "cfg": {"user_agent": 123},
        "key": "user_agent",
        "expect": None,
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "user_agent: expected str, got int",
        "covers": ["C000F002B0003"],
    },
]

OPT_INT_CASES = [
    {
        "name": "missing",
        "cfg": {},
        "key": "chunk_bytes",
        "expect": None,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F003B0001"],
    },
    {
        "name": "present_int",
        "cfg": {"chunk_bytes": 64},
        "key": "chunk_bytes",
        "expect": 64,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F003B0002"],
    },
    {
        "name": "present_wrong_type",
        "cfg": {"chunk_bytes": "64"},
        "key": "chunk_bytes",
        "expect": None,
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "chunk_bytes: expected int, got str",
        "covers": ["C000F003B0003"],
    },
]

OPT_FLOAT_CASES = [
    {
        "name": "missing",
        "cfg": {},
        "key": "timeout_s",
        "expect": None,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F004B0001"],
    },
    {
        "name": "present_int_cast",
        "cfg": {"timeout_s": 5},
        "key": "timeout_s",
        "expect": 5.0,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F004B0002"],
    },
    {
        "name": "present_float",
        "cfg": {"timeout_s": 2.5},
        "key": "timeout_s",
        "expect": 2.5,
        "expect_exc": None,
        "expect_sub": None,
        "covers": ["C000F004B0003"],
    },
    {
        "name": "present_wrong_type",
        "cfg": {"timeout_s": "x"},
        "key": "timeout_s",
        "expect": None,
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "timeout_s: expected float, got str",
        "covers": ["C000F004B0004"],
    },
]

PLAN_SINGLE_CASES = [
    {
        "name": "config_instance_id_and_config_precedence_injected",
        "strategy_name": "s",
        "strategy_cls": _DummyStrategy,
        "config": {"instance_id": "iid", "precedence": "5"},
        "ctor_kwargs": {},
        "depends_on": ("dep",),
        "expect_instance_id": "iid",
        "expect_precedence": 5,
        "expect_ctor": {"instance_id": "iid", "precedence": 5},
        "covers": [
            "C000F005B0001",
            "C000F005B0003",
            "C000F005B0006",
            "C000F005B0008",
            "C000F005B0010",
        ],
    },
    {
        "name": "fallback_instance_id_and_strategy_precedence",
        "strategy_name": "s2",
        "strategy_cls": _DummyStrategy,
        "config": {},
        "ctor_kwargs": {},
        "depends_on": (),
        "expect_instance_id": "s2",
        "expect_precedence": 777,
        "expect_ctor": {"instance_id": "s2", "precedence": 777},
        "covers": [
            "C000F005B0002",
            "C000F005B0004",
            "C000F005B0006",
            "C000F005B0008",
            "C000F005B0010",
        ],
    },
    {
        "name": "ctor_kwargs_already_has_instance_id_and_precedence",
        "strategy_name": "s3",
        "strategy_cls": _DummyStrategy,
        "config": {"instance_id": "cfg_iid", "precedence": 1},
        "ctor_kwargs": {"instance_id": "ctor_iid", "precedence": 999, "x": 1},
        "depends_on": (),
        "expect_instance_id": "cfg_iid",
        "expect_precedence": 1,
        "expect_ctor": {"instance_id": "ctor_iid", "precedence": 999, "x": 1},
        "covers": [
            "C000F005B0001",
            "C000F005B0003",
            "C000F005B0007",
            "C000F005B0009",
            "C000F005B0010",
        ],
    },
]

DEFAULTS_CASES = [
    {
        "name": "pep691_defaults",
        "cls": uut.Pep691IndexMetadataHttpStrategyConfig,
        "expect": {"timeout_s": 30.0, "user_agent": "project-resolution-engine/0", "precedence": 50},
        "covers": ["C002M001B0001"],
    },
    {
        "name": "http_wheel_defaults",
        "cls": uut.HttpWheelFileStrategyConfig,
        "expect": {
            "timeout_s": 120.0,
            "user_agent": "project-resolution-engine/0",
            "chunk_bytes": 1024 * 1024,
            "precedence": 50,
        },
        "covers": ["C003M001B0001"],
    },
    {
        "name": "pep658_defaults",
        "cls": uut.Pep658CoreMetadataHttpStrategyConfig,
        "expect": {"timeout_s": 30.0, "user_agent": "project-resolution-engine/0", "precedence": 50},
        "covers": ["C004M001B0001"],
    },
    {
        "name": "wheel_extracted_defaults",
        "cls": uut.WheelExtractedCoreMetadataStrategyConfig,
        "expect": {"wheel_strategy_id": "wheel_http", "wheel_timeout_s": 120.0, "precedence": 90},
        "covers": ["C005M001B0001"],
    },
    {
        "name": "direct_uri_wheel_defaults",
        "cls": uut.DirectUriWheelFileStrategyConfig,
        "expect": {"chunk_bytes": 1024 * 1024, "precedence": 40},
        "covers": ["C006M001B0001"],
    },
    {
        "name": "direct_uri_core_defaults",
        "cls": uut.DirectUriCoreMetadataStrategyConfig,
        "expect": {"precedence": 40},
        "covers": ["C007M001B0001"],
    },
]


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", UNKNOWN_KEYS_CASES, ids=lambda c: c["name"])
def test__unknown_keys(case: dict[str, object]) -> None:
    # covers: C000F001B0001, C000F001B0002
    if case["expect_exc"] is None:
        uut._unknown_keys(case["cfg"], case["allowed"], ctx=case["ctx"])  # type: ignore[arg-type]
        return

    with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
        uut._unknown_keys(case["cfg"], case["allowed"], ctx=case["ctx"])  # type: ignore[arg-type]
    assert case["expect_sub"] in str(ei.value)


@pytest.mark.parametrize("case", OPT_STR_CASES, ids=lambda c: c["name"])
def test__opt_str(case: dict[str, object]) -> None:
    # covers: C000F002B0001, C000F002B0002, C000F002B0003
    if case["expect_exc"] is None:
        assert uut._opt_str(case["cfg"], case["key"]) == case["expect"]  # type: ignore[arg-type]
        return

    with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
        uut._opt_str(case["cfg"], case["key"])  # type: ignore[arg-type]
    assert case["expect_sub"] in str(ei.value)


@pytest.mark.parametrize("case", OPT_INT_CASES, ids=lambda c: c["name"])
def test__opt_int(case: dict[str, object]) -> None:
    # covers: C000F003B0001, C000F003B0002, C000F003B0003
    if case["expect_exc"] is None:
        assert uut._opt_int(case["cfg"], case["key"]) == case["expect"]  # type: ignore[arg-type]
        return

    with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
        uut._opt_int(case["cfg"], case["key"])  # type: ignore[arg-type]
    assert case["expect_sub"] in str(ei.value)


@pytest.mark.parametrize("case", OPT_FLOAT_CASES, ids=lambda c: c["name"])
def test__opt_float(case: dict[str, object]) -> None:
    # covers: C000F004B0001, C000F004B0002, C000F004B0003, C000F004B0004
    if case["expect_exc"] is None:
        assert uut._opt_float(case["cfg"], case["key"]) == case["expect"]  # type: ignore[arg-type]
        return

    with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
        uut._opt_float(case["cfg"], case["key"])  # type: ignore[arg-type]
    assert case["expect_sub"] in str(ei.value)


@pytest.mark.parametrize("case", PLAN_SINGLE_CASES, ids=lambda c: c["name"])
def test__plan_single(case: dict[str, object]) -> None:
    # covers: C000F005B0001..B0010 (see per-row covers)
    plans = uut._plan_single(
        strategy_name=case["strategy_name"],  # type: ignore[arg-type]
        strategy_cls=case["strategy_cls"],  # type: ignore[arg-type]
        config=case["config"],  # type: ignore[arg-type]
        ctor_kwargs=case["ctor_kwargs"],  # type: ignore[arg-type]
        depends_on=case["depends_on"],  # type: ignore[arg-type]
    )

    assert isinstance(plans, list)
    assert len(plans) == 1
    p = plans[0]

    assert p.strategy_name == case["strategy_name"]
    assert p.instance_id == case["expect_instance_id"]
    assert p.precedence == case["expect_precedence"]
    assert p.depends_on == case["depends_on"]
    assert dict(p.ctor_kwargs) == dict(case["expect_ctor"])  # type: ignore[arg-type]


def test__plan_single_precedence_cast_errors_propagate() -> None:
    # covers: C000F005B0005
    with pytest.raises(ValueError):
        uut._plan_single(
            strategy_name="s",
            strategy_cls=_DummyStrategy,
            config={"precedence": "not-an-int"},
            ctor_kwargs={},
        )


# ---------------------------------------------------------------------------
# defaults()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", DEFAULTS_CASES, ids=lambda c: c["name"])
def test_config_spec_defaults(case: dict[str, object]) -> None:
    # covers: C002M001B0001, C003M001B0001, C004M001B0001, C005M001B0001, C006M001B0001, C007M001B0001
    cls = case["cls"]
    assert cls.defaults() == case["expect"]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# plan(): unknown keys (all specs)
# ---------------------------------------------------------------------------

PLAN_UNKNOWN_KEYS_CASES = [
    {
        "name": "pep691_unknown_key_raises",
        "spec": uut.Pep691IndexMetadataHttpStrategyConfig,
        "config": {"nope": True},
        "covers": ["C002M002B0001"],
    },
    {
        "name": "http_wheel_unknown_key_raises",
        "spec": uut.HttpWheelFileStrategyConfig,
        "config": {"nope": True},
        "covers": ["C003M002B0001"],
    },
    {
        "name": "pep658_unknown_key_raises",
        "spec": uut.Pep658CoreMetadataHttpStrategyConfig,
        "config": {"nope": True},
        "covers": ["C004M002B0001"],
    },
    {
        "name": "wheel_extracted_unknown_key_raises",
        "spec": uut.WheelExtractedCoreMetadataStrategyConfig,
        "config": {"nope": True},
        "covers": ["C005M002B0001"],
    },
    {
        "name": "direct_uri_wheel_unknown_key_raises",
        "spec": uut.DirectUriWheelFileStrategyConfig,
        "config": {"nope": True},
        "covers": ["C006M002B0001"],
    },
    {
        "name": "direct_uri_core_unknown_key_raises",
        "spec": uut.DirectUriCoreMetadataStrategyConfig,
        "config": {"nope": True},
        "covers": ["C007M002B0001"],
    },
]


@pytest.mark.parametrize("case", PLAN_UNKNOWN_KEYS_CASES, ids=lambda c: c["name"])
def test_config_spec_plan_unknown_keys_raise(case: dict[str, object]) -> None:
    # covers: per-row
    spec = case["spec"]
    with pytest.raises(uut.StrategyConfigError) as ei:
        spec.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert "unknown config keys" in str(ei.value)


# ---------------------------------------------------------------------------
# plan(): Pep691IndexMetadataHttpStrategyConfig
# ---------------------------------------------------------------------------

PEP691_PLAN_CASES = [
    {
        "name": "no_optionals",
        "config": {},
        "expect_ctor_keys": {"instance_id", "precedence"},
        # these are the missing arcs: 115->117 and 117->120
        "covers": ["C002M002B0002", "C002M002B0004", "C002M002B0007", "C002M002B0009"],
    },
    {
        "name": "timeout_and_user_agent_set",
        "config": {"timeout_s": 10, "user_agent": "ua"},
        "expect_ctor_subset": {"timeout_s": 10.0, "user_agent": "ua"},
        "covers": ["C002M002B0003", "C002M002B0006", "C002M002B0009"],
    },
    {
        "name": "timeout_wrong_type",
        "config": {"timeout_s": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "timeout_s: expected float",
        "covers": ["C002M002B0005"],
    },
    {
        "name": "user_agent_wrong_type",
        "config": {"user_agent": 1},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "user_agent: expected str",
        "covers": ["C002M002B0008"],
    },
]


@pytest.mark.parametrize("case", PEP691_PLAN_CASES, ids=lambda c: c["name"])
def test_pep691_plan(case: dict[str, object]) -> None:
    # covers: see per-row
    if case.get("expect_exc") is not None:
        with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
            uut.Pep691IndexMetadataHttpStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
        assert case["expect_sub"] in str(ei.value)
        return

    plans = uut.Pep691IndexMetadataHttpStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == uut.Pep691IndexMetadataHttpStrategyConfig.strategy_name

    ctor = dict(p.ctor_kwargs)
    if "expect_ctor_keys" in case:
        assert set(ctor.keys()) == set(case["expect_ctor_keys"])  # type: ignore[arg-type]
    if "expect_ctor_subset" in case:
        for k, v in case["expect_ctor_subset"].items():  # type: ignore[union-attr]
            assert ctor.get(k) == v


# ---------------------------------------------------------------------------
# plan(): HttpWheelFileStrategyConfig
# ---------------------------------------------------------------------------

HTTP_WHEEL_PLAN_CASES = [
    {
        "name": "no_optionals",
        "config": {},
        "expect_ctor_keys": {"instance_id", "precedence"},
        # missing arcs: 145->147, 147->149, 149->152
        "covers": ["C003M002B0002", "C003M002B0004", "C003M002B0007", "C003M002B0010", "C003M002B0012"],
    },
    {
        "name": "timeout_user_agent_chunk_bytes_set",
        "config": {"timeout_s": 1.0, "user_agent": "ua", "chunk_bytes": 7},
        "expect_ctor_subset": {"timeout_s": 1.0, "user_agent": "ua", "chunk_bytes": 7},
        "covers": ["C003M002B0003", "C003M002B0006", "C003M002B0009", "C003M002B0012"],
    },
    {
        "name": "chunk_bytes_wrong_type",
        "config": {"chunk_bytes": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "chunk_bytes: expected int",
        "covers": ["C003M002B0011"],
    },
    {
        "name": "timeout_wrong_type",
        "config": {"timeout_s": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "timeout_s: expected float",
        "covers": ["C003M002B0005"],
    },
    {
        "name": "user_agent_wrong_type",
        "config": {"user_agent": 1},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "user_agent: expected str",
        "covers": ["C003M002B0008"],
    },
]


@pytest.mark.parametrize("case", HTTP_WHEEL_PLAN_CASES, ids=lambda c: c["name"])
def test_http_wheel_plan(case: dict[str, object]) -> None:
    # covers: see per-row
    if case.get("expect_exc") is not None:
        with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
            uut.HttpWheelFileStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
        assert case["expect_sub"] in str(ei.value)
        return

    plans = uut.HttpWheelFileStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == uut.HttpWheelFileStrategyConfig.strategy_name

    ctor = dict(p.ctor_kwargs)
    if "expect_ctor_keys" in case:
        assert set(ctor.keys()) == set(case["expect_ctor_keys"])  # type: ignore[arg-type]
    if "expect_ctor_subset" in case:
        for k, v in case["expect_ctor_subset"].items():  # type: ignore[union-attr]
            assert ctor.get(k) == v


# ---------------------------------------------------------------------------
# plan(): Pep658CoreMetadataHttpStrategyConfig
# ---------------------------------------------------------------------------

PEP658_PLAN_CASES = [
    {
        "name": "no_optionals",
        "config": {},
        "expect_ctor_keys": {"instance_id", "precedence"},
        # missing arcs: 176->178, 178->181
        "covers": ["C004M002B0002", "C004M002B0004", "C004M002B0007", "C004M002B0009"],
    },
    {
        "name": "timeout_and_user_agent_set",
        "config": {"timeout_s": 2, "user_agent": "ua"},
        "expect_ctor_subset": {"timeout_s": 2.0, "user_agent": "ua"},
        "covers": ["C004M002B0003", "C004M002B0006", "C004M002B0009"],
    },
    {
        "name": "timeout_wrong_type",
        "config": {"timeout_s": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "timeout_s: expected float",
        "covers": ["C004M002B0005"],
    },
    {
        "name": "user_agent_wrong_type",
        "config": {"user_agent": 1},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "user_agent: expected str",
        "covers": ["C004M002B0008"],
    },
]


@pytest.mark.parametrize("case", PEP658_PLAN_CASES, ids=lambda c: c["name"])
def test_pep658_plan(case: dict[str, object]) -> None:
    # covers: see per-row
    if case.get("expect_exc") is not None:
        with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
            uut.Pep658CoreMetadataHttpStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
        assert case["expect_sub"] in str(ei.value)
        return

    plans = uut.Pep658CoreMetadataHttpStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == uut.Pep658CoreMetadataHttpStrategyConfig.strategy_name

    ctor = dict(p.ctor_kwargs)
    if "expect_ctor_keys" in case:
        assert set(ctor.keys()) == set(case["expect_ctor_keys"])  # type: ignore[arg-type]
    if "expect_ctor_subset" in case:
        for k, v in case["expect_ctor_subset"].items():  # type: ignore[union-attr]
            assert ctor.get(k) == v


# ---------------------------------------------------------------------------
# plan(): WheelExtractedCoreMetadataStrategyConfig
# ---------------------------------------------------------------------------

WHEEL_EXTRACTED_PLAN_CASES = [
    {
        "name": "wheel_strategy_id_truthy_timeout_set",
        "config": {"wheel_strategy_id": "direct", "wheel_timeout_s": 3.0, "precedence": 9},
        "expect_wheel_sid": "direct",
        "expect_timeout": 3.0,
        "expect_precedence": 9,
        "covers": ["C005M002B0002", "C005M002B0003", "C005M002B0006", "C005M002B0009"],
    },
    {
        "name": "wheel_strategy_id_missing_timeout_missing_defaults",
        "config": {},
        "expect_wheel_sid": "wheel_http",
        "expect_timeout": None,
        "expect_precedence": 777,
        "covers": ["C005M002B0002", "C005M002B0004", "C005M002B0007", "C005M002B0009"],
    },
    {
        "name": "wheel_strategy_id_wrong_type_raises",
        "config": {"wheel_strategy_id": 1},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "wheel_strategy_id: expected str",
        "covers": ["C005M002B0005"],
    },
    {
        "name": "wheel_timeout_wrong_type_raises",
        "config": {"wheel_timeout_s": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "wheel_timeout_s: expected float",
        "covers": ["C005M002B0008"],
    },
]


@pytest.mark.parametrize("case", WHEEL_EXTRACTED_PLAN_CASES, ids=lambda c: c["name"])
def test_wheel_extracted_plan(case: dict[str, object]) -> None:
    # covers: see per-row
    if case.get("expect_exc") is not None:
        with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
            uut.WheelExtractedCoreMetadataStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
        assert case["expect_sub"] in str(ei.value)
        return

    plans = uut.WheelExtractedCoreMetadataStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert len(plans) == 1

    p = plans[0]
    assert p.strategy_name == uut.WheelExtractedCoreMetadataStrategyConfig.strategy_name
    assert p.precedence == case["expect_precedence"]

    ctor = dict(p.ctor_kwargs)
    assert "wheel_strategy" in ctor
    ref = ctor["wheel_strategy"]
    assert isinstance(ref, uut.StrategyRef)
    assert ref.strategy_name == case["expect_wheel_sid"]  # type: ignore[index]
    assert ref.instance_id == case["expect_wheel_sid"]  # type: ignore[index]

    # depends_on is computed via wheel_ref.normalized_instance_id()
    assert p.depends_on == (case["expect_wheel_sid"],)  # type: ignore[index]

    if case["expect_timeout"] is None:
        assert "wheel_timeout_s" not in ctor
    else:
        assert ctor["wheel_timeout_s"] == case["expect_timeout"]


# ---------------------------------------------------------------------------
# plan(): DirectUri* configs
# ---------------------------------------------------------------------------

DIRECT_URI_WHEEL_PLAN_CASES = [
    {
        "name": "no_chunk_bytes",
        "config": {},
        "expect_ctor_keys": {"instance_id", "precedence"},
        # missing arc: 240->243
        "covers": ["C006M002B0002", "C006M002B0004", "C006M002B0006"],
    },
    {
        "name": "chunk_bytes_set",
        "config": {"chunk_bytes": 8, "precedence": 1},
        "expect_ctor_subset": {"chunk_bytes": 8, "precedence": 1},
        "covers": ["C006M002B0003", "C006M002B0006"],
    },
    {
        "name": "chunk_bytes_wrong_type",
        "config": {"chunk_bytes": "x"},
        "expect_exc": uut.StrategyConfigError,
        "expect_sub": "chunk_bytes: expected int",
        "covers": ["C006M002B0005"],
    },
]


@pytest.mark.parametrize("case", DIRECT_URI_WHEEL_PLAN_CASES, ids=lambda c: c["name"])
def test_direct_uri_wheel_plan(case: dict[str, object]) -> None:
    # covers: see per-row
    if case.get("expect_exc") is not None:
        with pytest.raises(case["expect_exc"]) as ei:  # type: ignore[arg-type]
            uut.DirectUriWheelFileStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
        assert case["expect_sub"] in str(ei.value)
        return

    plans = uut.DirectUriWheelFileStrategyConfig.plan(strategy_cls=_DummyStrategy, config=case["config"])  # type: ignore[arg-type]
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == uut.DirectUriWheelFileStrategyConfig.strategy_name

    ctor = dict(p.ctor_kwargs)
    if "expect_ctor_keys" in case:
        assert set(ctor.keys()) == set(case["expect_ctor_keys"])  # type: ignore[arg-type]
    if "expect_ctor_subset" in case:
        for k, v in case["expect_ctor_subset"].items():  # type: ignore[union-attr]
            assert ctor.get(k) == v


def test_direct_uri_core_plan_success() -> None:
    # covers: C007M002B0002, C007M002B0003
    plans = uut.DirectUriCoreMetadataStrategyConfig.plan(strategy_cls=_DummyStrategy, config={})
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == uut.DirectUriCoreMetadataStrategyConfig.strategy_name
    assert dict(p.ctor_kwargs) == {"instance_id": p.instance_id, "precedence": p.precedence}


# ---------------------------------------------------------------------------
# plan(): precedence cast error propagation per-spec (caller return lines)
# ---------------------------------------------------------------------------

PRECEDENCE_CAST_ERROR_CASES = [
    {
        "name": "pep691_precedence_bad",
        "spec": uut.Pep691IndexMetadataHttpStrategyConfig,
        "covers": ["C002M002B0010"],
    },
    {
        "name": "http_wheel_precedence_bad",
        "spec": uut.HttpWheelFileStrategyConfig,
        "covers": ["C003M002B0013"],
    },
    {
        "name": "pep658_precedence_bad",
        "spec": uut.Pep658CoreMetadataHttpStrategyConfig,
        "covers": ["C004M002B0010"],
    },
    {
        "name": "wheel_extracted_precedence_bad",
        "spec": uut.WheelExtractedCoreMetadataStrategyConfig,
        "covers": ["C005M002B0010"],
    },
    {
        "name": "direct_uri_wheel_precedence_bad",
        "spec": uut.DirectUriWheelFileStrategyConfig,
        "covers": ["C006M002B0007"],
    },
    {
        "name": "direct_uri_core_precedence_bad",
        "spec": uut.DirectUriCoreMetadataStrategyConfig,
        "covers": ["C007M002B0004"],
    },
]


@pytest.mark.parametrize("case", PRECEDENCE_CAST_ERROR_CASES, ids=lambda c: c["name"])
def test_config_spec_plan_precedence_cast_error_propagates(case: dict[str, object]) -> None:
    # covers: see per-row
    spec = case["spec"]
    with pytest.raises(ValueError):
        spec.plan(strategy_cls=_DummyStrategy, config={"precedence": "nope"})  # type: ignore[arg-type]
