import types
from typing import Any, Mapping

import pytest

from project_resolution_engine.internal.util import strategy as strat
from project_resolution_engine.strategies import (
    BaseArtifactResolutionStrategy,
    InstantiationPolicy,
    StrategyCriticality,
)


# --------------------------------------------------------------------------------------
# Helpers (not tests)
# --------------------------------------------------------------------------------------

class _DummyPkg:
    __name__ = "dummy_pkg"
    __path__ = ["<dummy>"]


class _EP:
    def __init__(self, obj: Any):
        self._obj = obj

    def load(self) -> Any:
        return self._obj


# --------------------------------------------------------------------------------------
# StrategyRef.normalized_instance_id
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "strategy_name, instance_id, expect, expect_err_substr, covers",
    [
        # covers: C002M001B0001
        ("", "", None, "StrategyRef requires strategy_name or instance_id", ["C002M001B0001"]),
        # covers: C002M001B0002
        ("s", "", "s", None, ["C002M001B0002"]),
        # also covers: C002M001B0002 (instance_id wins)
        ("s", "iid", "iid", None, ["C002M001B0002"]),
    ],
)
def test_strategyref_normalized_instance_id(strategy_name, instance_id, expect, expect_err_substr, covers):
    ref = strat.StrategyRef(strategy_name=strategy_name, instance_id=instance_id)
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            ref.normalized_instance_id()
        assert expect_err_substr in str(e.value)
    else:
        assert ref.normalized_instance_id() == expect


# --------------------------------------------------------------------------------------
# BaseArtifactResolutionStrategyConfig (defaults / plan)
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_base_config_defaults_and_plan():
    # covers: C004M001B0001, C004M002B0001
    assert strat.BaseArtifactResolutionStrategyConfig.defaults() == {}
    with pytest.raises(NotImplementedError):
        strat.BaseArtifactResolutionStrategyConfig.plan(strategy_cls=object, config={})


# --------------------------------------------------------------------------------------
# DefaultStrategyConfig.plan
# --------------------------------------------------------------------------------------

class _StrategyNameAttr:
    strategy_name = "from_attr"


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "cfg, expect_err_substr, covers",
    [
        # covers: C005M001B0001
        ({"strategy_name": 123, "instance_id": "x"}, "strategy_name must be a non-empty string", ["C005M001B0001"]),
        # covers: C005M001B0003
        ({"strategy_name": "s", "instance_id": 5}, "instance_id must be a non-empty string", ["C005M001B0003"]),
        # covers: C005M001B0005
        (
                {"strategy_name": "s", "instance_id": "x", "precedence": "nope"},
                "precedence: expected int",
                ["C005M001B0005"],
        ),
    ],
)
def test_default_strategy_config_plan_validation(cfg, expect_err_substr, covers):
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.DefaultStrategyConfig.plan(strategy_cls=_StrategyNameAttr, config=cfg)
    assert expect_err_substr in str(e.value)


# noinspection PyTypeChecker
def test_default_strategy_config_plan_validation_fallback_invalid_strategy_name(monkeypatch):
    # covers: C005M001B0001 (fallback via _strategy_name_for_class produces invalid value)
    monkeypatch.setattr(strat, "_strategy_name_for_class", lambda cls: "")
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.DefaultStrategyConfig.plan(
            strategy_cls=_StrategyNameAttr,
            config={"strategy_name": "", "instance_id": "x"},
        )
    assert "strategy_name must be a non-empty string" in str(e.value)


# noinspection PyTypeChecker
def test_default_strategy_config_plan_success_and_ctor_kwarg_stripping():
    # covers: C005M001B0002, C005M001B0004, C005M001B0006
    cfg = {
        # omit strategy_name so it must be discovered via _strategy_name_for_class
        "instance_id": "iid1",
        "precedence": 12,
        "criticality": StrategyCriticality.REQUIRED,
        "foo": "bar",
        "nested": {"x": 1},
    }
    plans = strat.DefaultStrategyConfig.plan(strategy_cls=_StrategyNameAttr, config=cfg)
    assert len(plans) == 1
    p = plans[0]
    assert p.strategy_name == "from_attr"
    assert p.instance_id == "iid1"
    assert p.precedence == 12
    assert p.ctor_kwargs == {"foo": "bar", "nested": {"x": 1}}
    assert p.depends_on == ()


# --------------------------------------------------------------------------------------
# _iter_module_objects
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_iter_module_objects_empty_package_name_raises_value_error():
    # covers: C000F001B0001
    g = strat._iter_module_objects("")
    with pytest.raises(ValueError):
        next(g)


def test_iter_module_objects_walk_packages_zero_modules(monkeypatch):
    # covers: C000F001B0002, C000F001B0003
    monkeypatch.setattr(strat.importlib, "import_module", lambda name: _DummyPkg())
    monkeypatch.setattr(strat.pkgutil, "walk_packages", lambda *args, **kwargs: [])
    assert list(strat._iter_module_objects("dummy_pkg")) == []


def test_iter_module_objects_walk_packages_yields_objects(monkeypatch):
    # covers: C000F001B0004
    def _import_module(name: str):
        if name == "dummy_pkg":
            return _DummyPkg()
        if name == "dummy_pkg.mod1":
            m = types.SimpleNamespace()
            m.a = 1
            m.b = "x"
            return m
        raise ImportError(name)

    monkeypatch.setattr(strat.importlib, "import_module", _import_module)
    monkeypatch.setattr(strat.pkgutil, "walk_packages", lambda *a, **k: [(None, "dummy_pkg.mod1", False)])
    out = list(strat._iter_module_objects("dummy_pkg"))
    assert 1 in out
    assert "x" in out


# --------------------------------------------------------------------------------------
# _iter_entrypoint_objects
# --------------------------------------------------------------------------------------

def test_iter_entrypoint_objects_empty_group_and_no_eps(monkeypatch):
    # covers: C000F002B0001, C000F002B0003
    class _EPS:
        def select(self, *, group: str):
            assert group == ""
            return []

    monkeypatch.setattr(strat, "entry_points", lambda: _EPS())
    assert list(strat._iter_entrypoint_objects("")) == []


def test_iter_entrypoint_objects_group_with_eps(monkeypatch):
    # covers: C000F002B0002, C000F002B0004
    class _EPS:
        def select(self, *, group: str):
            assert group == "g1"
            return [_EP(1), _EP("x")]

    monkeypatch.setattr(strat, "entry_points", lambda: _EPS())
    assert list(strat._iter_entrypoint_objects("g1")) == [1, "x"]


# --------------------------------------------------------------------------------------
# builtin / entrypoint discovery filters
# --------------------------------------------------------------------------------------

class _AbstractStrategy(BaseArtifactResolutionStrategy[Any]):
    # abstract is OK for issubclass checks
    def resolve(self, *, key: Any, destination_uri: str):
        raise NotImplementedError


class _NotAStrategy:
    pass


def test_builtin_strategy_classes_empty(monkeypatch):
    # covers: C000F003B0001
    monkeypatch.setattr(strat, "_iter_module_objects", lambda package_name: iter(()))
    assert strat._builtin_strategy_classes("pkg") == []


def test_builtin_strategy_classes_filters(monkeypatch):
    # covers: C000F003B0002, C000F003B0003, C000F003B0004
    monkeypatch.setattr(
        strat,
        "_iter_module_objects",
        lambda package_name: iter([_AbstractStrategy, 123, _NotAStrategy]),
    )
    out = strat._builtin_strategy_classes("pkg")
    assert out == [_AbstractStrategy]


def test_entrypoint_strategy_classes_filters(monkeypatch):
    # covers: C000F004B0001..B0004
    monkeypatch.setattr(
        strat,
        "_iter_entrypoint_objects",
        lambda group: iter([_AbstractStrategy, 123, _NotAStrategy]),
    )
    out = strat._entrypoint_strategy_classes("g")
    assert out == [_AbstractStrategy]


class _SpecA(strat.BaseArtifactResolutionStrategyConfig):
    strategy_name = "a"


class _SpecB(strat.BaseArtifactResolutionStrategyConfig):
    strategy_name = "b"


def test_builtin_config_spec_classes_empty(monkeypatch):
    # covers: C000F005B0001
    monkeypatch.setattr(strat, "_iter_module_objects", lambda package_name: iter(()))
    assert strat._builtin_config_spec_classes("pkg") == []


def test_builtin_config_spec_classes_filters(monkeypatch):
    # covers: C000F005B0002..B0004
    monkeypatch.setattr(strat, "_iter_module_objects", lambda package_name: iter([_SpecA, 123, _NotAStrategy]))
    assert strat._builtin_config_spec_classes("pkg") == [_SpecA]


def test_entrypoint_config_spec_classes_filters(monkeypatch):
    # covers: C000F006B0001..B0004
    monkeypatch.setattr(strat, "_iter_entrypoint_objects", lambda group: iter([_SpecA, 123, _NotAStrategy]))
    assert strat._entrypoint_config_spec_classes("g") == [_SpecA]


# --------------------------------------------------------------------------------------
# _strategy_name_for_class
# --------------------------------------------------------------------------------------

class _HasStrategyName:
    strategy_name = "sn"


class _HasNameOnly:
    name = "nm"


class _HasNeither:
    pass


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "cls, expected, covers",
    [
        (_HasStrategyName, "sn", ["C000F007B0001"]),
        (_HasNameOnly, "nm", ["C000F007B0002", "C000F007B0003"]),
        (_HasNeither, "_HasNeither", ["C000F007B0002", "C000F007B0004"]),
    ],
)
def test_strategy_name_for_class(cls, expected, covers):
    assert strat._strategy_name_for_class(cls) == expected


# --------------------------------------------------------------------------------------
# discover_strategy_classes
# --------------------------------------------------------------------------------------

def test_discover_strategy_classes_no_strategies(monkeypatch):
    # covers: C000F008B0001, C000F008B0005
    monkeypatch.setattr(strat, "_builtin_strategy_classes", lambda pkg: [])
    monkeypatch.setattr(strat, "_entrypoint_strategy_classes", lambda grp: [])
    out = strat.discover_strategy_classes(strategy_package="p", strategy_entrypoint_group="g")
    assert out == {}


def test_discover_strategy_classes_duplicate_in_builtin(monkeypatch):
    # covers: C000F008B0002, C000F008B0003
    class A:
        strategy_name = "dup"

    class B:
        strategy_name = "dup"

    monkeypatch.setattr(strat, "_builtin_strategy_classes", lambda pkg: [A, B])
    monkeypatch.setattr(strat, "_entrypoint_strategy_classes", lambda grp: [])
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.discover_strategy_classes(strategy_package="p", strategy_entrypoint_group="g")
    assert "duplicate strategy_name discovered" in str(e.value)


def test_discover_strategy_classes_duplicate_between_builtin_and_entrypoint(monkeypatch):
    # covers: C000F008B0004, C000F008B0006, C000F008B0007
    class A:
        strategy_name = "dup"

    class C:
        strategy_name = "dup"

    monkeypatch.setattr(strat, "_builtin_strategy_classes", lambda pkg: [A])
    monkeypatch.setattr(strat, "_entrypoint_strategy_classes", lambda grp: [C])
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.discover_strategy_classes(strategy_package="p", strategy_entrypoint_group="g")
    assert "duplicate strategy_name discovered" in str(e.value)


def test_discover_strategy_classes_success_with_origins(monkeypatch):
    # covers: C000F008B0004, C000F008B0008
    class A:
        strategy_name = "a"

    class B:
        strategy_name = "b"

    monkeypatch.setattr(strat, "_builtin_strategy_classes", lambda pkg: [A])
    monkeypatch.setattr(strat, "_entrypoint_strategy_classes", lambda grp: [B])
    out = strat.discover_strategy_classes(strategy_package="p", strategy_entrypoint_group="g")
    assert out["a"].origin == "builtin"
    assert out["b"].origin == "entrypoint"


# --------------------------------------------------------------------------------------
# discover_config_specs
# --------------------------------------------------------------------------------------

def test_discover_config_specs_empty(monkeypatch):
    # covers: C000F009B0001
    monkeypatch.setattr(strat, "_builtin_config_spec_classes", lambda pkg: [])
    monkeypatch.setattr(strat, "_entrypoint_config_spec_classes", lambda grp: [])
    assert strat.discover_config_specs(builtin_config_package="p", config_entrypoint_group="g") == {}


def test_discover_config_specs_filters_and_registers(monkeypatch):
    # covers: C000F009B0002, C000F009B0003, C000F009B0004, C000F009B0006
    class NoName:
        strategy_name = ""

    class NotStr:
        strategy_name = 1

    class Ok:
        strategy_name = "ok"

    monkeypatch.setattr(strat, "_builtin_config_spec_classes", lambda pkg: [NoName, NotStr, Ok])
    monkeypatch.setattr(strat, "_entrypoint_config_spec_classes", lambda grp: [])
    out = strat.discover_config_specs(builtin_config_package="p", config_entrypoint_group="g")
    assert out == {"ok": Ok}


def test_discover_config_specs_duplicate(monkeypatch):
    # covers: C000F009B0005
    class A:
        strategy_name = "dup"

    class B:
        strategy_name = "dup"

    monkeypatch.setattr(strat, "_builtin_config_spec_classes", lambda pkg: [A])
    monkeypatch.setattr(strat, "_entrypoint_config_spec_classes", lambda grp: [B])
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.discover_config_specs(builtin_config_package="p", config_entrypoint_group="g")
    assert "duplicate config spec" in str(e.value)


# --------------------------------------------------------------------------------------
# _ensure_dict / _effective_precedence / _effective_criticality
# --------------------------------------------------------------------------------------

def test_ensure_dict_returns_copy():
    # covers: C000F010B0001
    src = {"a": 1}
    out = strat._ensure_dict(src)
    assert out == src
    assert out is not src


class _PrecInt:
    precedence = 7


class _PrecNonInt:
    precedence = "x"


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "cfg, strategy_cls, fallback, expect, expect_err_substr, covers",
    [
        # covers: C000F011B0001, C000F011B0004
        ({"precedence": 3}, _PrecNonInt, 99, 3, None, ["C000F011B0001", "C000F011B0004"]),
        # covers: C000F011B0003
        ({"precedence": "no"}, _PrecInt, 99, None, "precedence: expected int", ["C000F011B0001", "C000F011B0003"]),
        # covers: C000F011B0002, C000F011B0005
        ({}, _PrecNonInt, 11, 11, None, ["C000F011B0002", "C000F011B0005"]),
        # covers: C000F011B0002, C000F011B0006
        ({}, _PrecInt, 11, 7, None, ["C000F011B0002", "C000F011B0006"]),
    ],
)
def test_effective_precedence(cfg, strategy_cls, fallback, expect, expect_err_substr, covers):
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            strat._effective_precedence(cfg=cfg, strategy_cls=strategy_cls, fallback=fallback)
        assert expect_err_substr in str(e.value)
    else:
        assert strat._effective_precedence(cfg=cfg, strategy_cls=strategy_cls, fallback=fallback) == expect


class _CritEnum:
    criticality = StrategyCriticality.IMPERATIVE


class _CritStrValid:
    criticality = "required"


class _CritStrInvalid:
    criticality = "nope"


class _CritOther:
    criticality = 123


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "cfg, strategy_cls, expect, expect_err_substr, covers",
    [
        # covers: C000F012B0001, C000F012B0003
        ({"criticality": StrategyCriticality.REQUIRED}, _CritOther, StrategyCriticality.REQUIRED, None,
         ["C000F012B0001", "C000F012B0003"]),
        # covers: C000F012B0001, C000F012B0004, C000F012B0006
        ({"criticality": "required"}, _CritOther, StrategyCriticality.REQUIRED, None,
         ["C000F012B0001", "C000F012B0004", "C000F012B0006"]),
        # covers: C000F012B0001, C000F012B0004, C000F012B0007
        ({"criticality": "invalid"}, _CritOther, None, "criticality: invalid value",
         ["C000F012B0001", "C000F012B0004", "C000F012B0007"]),
        # covers: C000F012B0001, C000F012B0005
        ({"criticality": 123}, _CritOther, None, "criticality: expected StrategyCriticality or str",
         ["C000F012B0001", "C000F012B0005"]),
        # covers: C000F012B0002, C000F012B0008
        ({}, _CritEnum, StrategyCriticality.IMPERATIVE, None, ["C000F012B0002", "C000F012B0008"]),
        # covers: C000F012B0002, C000F012B0009, C000F012B0011
        ({}, _CritStrValid, StrategyCriticality.REQUIRED, None, ["C000F012B0002", "C000F012B0009", "C000F012B0011"]),
        # covers: C000F012B0002, C000F012B0009, C000F012B0012
        ({}, _CritStrInvalid, StrategyCriticality.OPTIONAL, None, ["C000F012B0002", "C000F012B0009", "C000F012B0012"]),
        # covers: C000F012B0002, C000F012B0010
        ({}, _CritOther, StrategyCriticality.OPTIONAL, None, ["C000F012B0002", "C000F012B0010"]),
    ],
)
def test_effective_criticality(cfg, strategy_cls, expect, expect_err_substr, covers):
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            strat._effective_criticality(cfg=cfg, strategy_cls=strategy_cls)
        assert expect_err_substr in str(e.value)
    else:
        assert strat._effective_criticality(cfg=cfg, strategy_cls=strategy_cls) == expect


# --------------------------------------------------------------------------------------
# _scan_deps
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "val, expect_deps, covers",
    [
        # covers: C000F013B0001
        (strat.StrategyRef(strategy_name="a"), {"a"}, ["C000F013B0001"]),
        # covers: C000F013B0003, C000F013B0005
        ({}, set(), ["C000F013B0003", "C000F013B0005"]),
        # covers: C000F013B0003, C000F013B0006
        ({"x": strat.StrategyRef(strategy_name="b")}, {"b"}, ["C000F013B0003", "C000F013B0006"]),
        # covers: C000F013B0007, C000F013B0009
        ([], set(), ["C000F013B0007", "C000F013B0009"]),
        # covers: C000F013B0007, C000F013B0010
        ([strat.StrategyRef(strategy_name="c")], {"c"}, ["C000F013B0007", "C000F013B0010"]),
        # covers: C000F013B0007 (tuple path)
        ((strat.StrategyRef(strategy_name="d"),), {"d"}, ["C000F013B0007", "C000F013B0010"]),
        # covers: C000F013B0008
        ("nope", set(), ["C000F013B0008"]),
    ],
)
def test_scan_deps(val, expect_deps, covers):
    out: set[str] = set()
    strat._scan_deps(val, out)
    assert out == expect_deps


# --------------------------------------------------------------------------------------
# build_strategy_plans (top-level early exits)
# --------------------------------------------------------------------------------------

def test_build_strategy_plans_no_plans(monkeypatch):
    # covers: C000F014B0001
    ingested = strat._IngestedConfigs(cfg_by_instance_id={}, bound_iids_by_strategy={})
    monkeypatch.setattr(strat, "_ingest_raw_configs", lambda **kwargs: ingested)
    monkeypatch.setattr(strat, "_plan_all_strategies", lambda **kwargs: ([], {}))
    assert strat.build_strategy_plans(strategy_classes={}, config_specs={}, raw_configs_by_instance_id=None) == []


# noinspection PyTypeChecker
def test_build_strategy_plans_no_enabled_plans(monkeypatch):
    # covers: C000F014B0002, C000F014B0003
    ingested = strat._IngestedConfigs(cfg_by_instance_id={}, bound_iids_by_strategy={})
    monkeypatch.setattr(strat, "_ingest_raw_configs", lambda **kwargs: ingested)

    dummy_plan = strat.StrategyPlan(
        strategy_name="s", instance_id="s", strategy_cls=object, ctor_kwargs={}, depends_on=(), precedence=1
    )
    monkeypatch.setattr(strat, "_plan_all_strategies", lambda **kwargs: ([dummy_plan], {"s": {"instance_id": "s"}}))
    monkeypatch.setattr(strat, "_enable_plans", lambda **kwargs: ([], {}))
    assert strat.build_strategy_plans(strategy_classes={}, config_specs={}, raw_configs_by_instance_id=None) == []


# noinspection PyTypeChecker
def test_build_strategy_plans_success_calls_validation(monkeypatch):
    # covers: C000F014B0004
    ingested = strat._IngestedConfigs(cfg_by_instance_id={}, bound_iids_by_strategy={})
    monkeypatch.setattr(strat, "_ingest_raw_configs", lambda **kwargs: ingested)

    dummy_plan = strat.StrategyPlan(
        strategy_name="s", instance_id="s", strategy_cls=object, ctor_kwargs={}, depends_on=(), precedence=1
    )
    monkeypatch.setattr(strat, "_plan_all_strategies", lambda **kwargs: ([dummy_plan], {"s": {"instance_id": "s"}}))

    enabled = [
        strat.StrategyPlan(
            strategy_name="s", instance_id="s", strategy_cls=object, ctor_kwargs={}, depends_on=(), precedence=1
        )
    ]
    monkeypatch.setattr(strat, "_enable_plans", lambda **kwargs: (enabled, {"s": StrategyCriticality.OPTIONAL}))

    called = {"deps": 0, "closure": 0}
    monkeypatch.setattr(
        strat,
        "_validate_enabled_dependencies_exist",
        lambda plans: called.__setitem__("deps", called["deps"] + 1),
    )
    monkeypatch.setattr(
        strat,
        "_enforce_imperative_closure",
        lambda **kw: called.__setitem__("closure", called["closure"] + 1),
    )

    out = strat.build_strategy_plans(strategy_classes={}, config_specs={}, raw_configs_by_instance_id=None)
    assert out == enabled
    assert called["deps"] == 1
    assert called["closure"] == 1


# --------------------------------------------------------------------------------------
# _ingest_raw_configs and its validators
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "iid, expect_err_substr, covers",
    [
        (None, "strategy config keys must be non empty strings", ["C000F016B0001"]),
        ("", "strategy config keys must be non empty strings", ["C000F016B0001"]),
        ("ok", None, ["C000F016B0002"]),
    ],
)
def test_validate_instance_id_key(iid, expect_err_substr, covers):
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            strat._validate_instance_id_key(iid)
        assert expect_err_substr in str(e.value)
    else:
        strat._validate_instance_id_key(iid)


def test_validate_raw_cfg_mapping_raises_for_non_mapping():
    # covers: C000F017B0001
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._validate_raw_cfg_mapping("x", 123)
    assert "must be a mapping" in str(e.value)


def test_validate_raw_cfg_mapping_ok():
    # covers: C000F017B0002
    strat._validate_raw_cfg_mapping("x", {})


def test_validate_or_set_cfg_instance_id_mismatch_raises():
    # covers: C000F018B0001
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._validate_or_set_cfg_instance_id("x", {"instance_id": "y"})
    assert "config instance_id mismatch" in str(e.value)


def test_validate_or_set_cfg_instance_id_sets_value():
    # covers: C000F018B0002
    cfg: dict[str, Any] = {}
    strat._validate_or_set_cfg_instance_id("x", cfg)
    assert cfg["instance_id"] == "x"


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "iid, cfg, strategy_classes, expect, expect_err_substr, covers",
    [
        # covers: C000F019B0001, C000F019B0006
        ("a", {}, {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")}, "a", None,
         ["C000F019B0001", "C000F019B0006"]),
        # covers: C000F019B0002, C000F019B0006
        ("a", {"strategy_name": "a"}, {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")}, "a", None,
         ["C000F019B0002", "C000F019B0006"]),
        # covers: C000F019B0003
        ("a", {"strategy_name": ""}, {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")}, None,
         "must be a non empty string", ["C000F019B0003"]),
        # covers: C000F019B0005
        ("a", {"strategy_name": "missing"}, {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")},
         None, "unknown strategy_name", ["C000F019B0005"]),
    ],
)
def test_normalize_and_validate_strategy_name(iid, cfg, strategy_classes, expect, expect_err_substr, covers):
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            strat._normalize_and_validate_strategy_name(iid=iid, cfg=dict(cfg), strategy_classes=strategy_classes)
        assert expect_err_substr in str(e.value)
    else:
        assert strat._normalize_and_validate_strategy_name(iid=iid, cfg=dict(cfg),
                                                           strategy_classes=strategy_classes) == expect


# noinspection PyTypeChecker
def test_ingest_raw_configs_none_or_empty():
    # covers: C000F015B0001, C000F015B0003
    strategy_classes = {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")}
    out = strat._ingest_raw_configs(raw_configs_by_instance_id=None, strategy_classes=strategy_classes)
    assert out.cfg_by_instance_id == {}
    assert out.bound_iids_by_strategy == {}


# noinspection PyTypeChecker
def test_ingest_raw_configs_success_binds_instance():
    # covers: C000F015B0002, C000F015B0004
    strategy_classes = {"a": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")}
    out = strat._ingest_raw_configs(raw_configs_by_instance_id={"a": {}}, strategy_classes=strategy_classes)
    assert out.cfg_by_instance_id["a"]["instance_id"] == "a"
    assert out.cfg_by_instance_id["a"]["strategy_name"] == "a"
    assert out.bound_iids_by_strategy == {"a": ["a"]}


# --------------------------------------------------------------------------------------
# _select_instance_ids_for_strategy / _enforce_singleton_policy
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "origin, initial_iids, expect_iids, expect_defaults_key, covers",
    [
        ("entrypoint", [], [], None, ["C000F021B0001"]),
        ("entrypoint", ["x"], ["x"], None, ["C000F021B0002"]),
        ("builtin", [], ["s"], "s", ["C000F021B0003"]),
        ("builtin", ["x"], ["x"], None, ["C000F021B0004"]),
    ],
)
def test_select_instance_ids_for_strategy(origin, initial_iids, expect_iids, expect_defaults_key, covers):
    info = strat._StrategyClassInfo(strategy_cls=object, origin=origin)
    defaults: dict[str, dict[str, Any]] = {}
    out = strat._select_instance_ids_for_strategy(
        strategy_name="s",
        info=info,
        iids=list(initial_iids),
        spec_cls=strat.DefaultStrategyConfig,
        defaults_cfg_by_iid=defaults,
    )
    assert out == expect_iids
    if expect_defaults_key:
        assert expect_defaults_key in defaults
    else:
        assert defaults == {}


@pytest.mark.parametrize(
    "policy, iids, expect_err_substr, covers",
    [
        (InstantiationPolicy.SINGLETON, [], "is SINGLETON but 0 instances were configured", ["C000F022B0001"]),
        (InstantiationPolicy.SINGLETON, ["x", "y"], "is SINGLETON but 2 instances were configured", ["C000F022B0001"]),
        (InstantiationPolicy.SINGLETON, ["x"], "instance_id 'x' != strategy_name", ["C000F022B0002"]),
        (InstantiationPolicy.SINGLETON, ["s"], None, ["C000F022B0003"]),
        (InstantiationPolicy.PROTOTYPE, ["x", "y"], None, ["C000F022B0004"]),
    ],
)
def test_enforce_singleton_policy(policy, iids, expect_err_substr, covers):
    if expect_err_substr:
        with pytest.raises(strat.StrategyConfigError) as e:
            strat._enforce_singleton_policy(strategy_name="s", policy=policy, iids=iids)
        assert expect_err_substr in str(e.value)
    else:
        strat._enforce_singleton_policy(strategy_name="s", policy=policy, iids=iids)


# --------------------------------------------------------------------------------------
# _plan_all_strategies
# --------------------------------------------------------------------------------------

def test_plan_all_strategies_no_strategies():
    # covers: C000F020B0001
    plans, effective = strat._plan_all_strategies(
        strategy_classes={},
        config_specs={},
        cfg_by_instance_id={},
        bound_iids_by_strategy={},
    )
    assert plans == []
    assert effective == {}


# noinspection PyTypeChecker
def test_plan_all_strategies_entrypoint_no_iids_produces_no_plans():
    # covers: C000F020B0002, C000F020B0003
    class EntryProto:
        instantiation_policy = InstantiationPolicy.PROTOTYPE

    strategy_classes = {
        "s": strat._StrategyClassInfo(strategy_cls=EntryProto, origin="entrypoint"),
    }
    plans, effective = strat._plan_all_strategies(
        strategy_classes=strategy_classes,
        config_specs={},
        cfg_by_instance_id={},
        bound_iids_by_strategy={},
    )
    assert plans == []
    assert effective == {}


# noinspection PyTypeChecker
def test_plan_all_strategies_internal_missing_config_raises():
    # covers: C000F020B0005
    class EntryProto2:
        instantiation_policy = InstantiationPolicy.PROTOTYPE

    strategy_classes = {
        "s": strat._StrategyClassInfo(strategy_cls=EntryProto2, origin="entrypoint"),
    }
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._plan_all_strategies(
            strategy_classes=strategy_classes,
            config_specs={},
            cfg_by_instance_id={},  # missing iid 'x'
            bound_iids_by_strategy={"s": ["x"]},
        )
    assert "internal error: missing config" in str(e.value)


# noinspection PyTypeChecker
def test_plan_all_strategies_success_builtin_defaults_and_entrypoint_bound():
    # covers: C000F020B0004, C000F020B0006
    class Builtin:
        instantiation_policy = InstantiationPolicy.SINGLETON
        precedence = 5

    class Entry:
        instantiation_policy = InstantiationPolicy.PROTOTYPE

    strategy_classes = {
        "builtin": strat._StrategyClassInfo(strategy_cls=Builtin, origin="builtin"),
        "entry": strat._StrategyClassInfo(strategy_cls=Entry, origin="entrypoint"),
    }

    cfg_by_instance_id = {"entry1": {"instance_id": "entry1", "strategy_name": "entry", "foo": 1}}
    bound = {"entry": ["entry1"]}

    class Spec(strat.BaseArtifactResolutionStrategyConfig):
        strategy_name = "entry"

        @classmethod
        def defaults(cls) -> Mapping[str, Any]:
            return {"d": 9}

        @classmethod
        def plan(cls, *, strategy_cls, config):
            return [
                strat.StrategyPlan(
                    strategy_name=config["strategy_name"],
                    instance_id=config["instance_id"],
                    strategy_cls=strategy_cls,
                    ctor_kwargs={"foo": config.get("foo"), "d": config.get("d")},
                    depends_on=(),
                    precedence=config.get("precedence", 100),
                )
            ]

    plans, effective = strat._plan_all_strategies(
        strategy_classes=strategy_classes,
        config_specs={"entry": Spec},
        cfg_by_instance_id=cfg_by_instance_id,
        bound_iids_by_strategy=bound,
    )

    # builtin default creates instance_id == strategy_name
    assert "builtin" in effective
    assert effective["builtin"]["instance_id"] == "builtin"
    # entry uses merged defaults
    assert effective["entry1"]["d"] == 9
    assert {p.instance_id for p in plans} == {"builtin", "entry1"}


# --------------------------------------------------------------------------------------
# _enable_plans / _strip_planner_keys
# --------------------------------------------------------------------------------------

def test_strip_planner_keys():
    # covers: C000F024B0001
    out = strat._strip_planner_keys(
        {"strategy_name": "s", "instance_id": "i", "precedence": 1, "criticality": "x", "keep": 2}
    )
    assert out == {"keep": 2}


def test_enable_plans_empty_list():
    # covers: C000F023B0001
    enabled, crit = strat._enable_plans(plans=[], effective_cfg_by_iid={})
    assert enabled == []
    assert crit == {}


# noinspection PyTypeChecker
def test_enable_plans_duplicate_instance_id_raises():
    # covers: C000F023B0003
    p1 = strat.StrategyPlan("s", "iid", object, {}, (), 1)
    p2 = strat.StrategyPlan("s", "iid", object, {}, (), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._enable_plans(plans=[p1, p2], effective_cfg_by_iid={"iid": {"instance_id": "iid"}})
    assert "duplicate instance_id planned" in str(e.value)


# noinspection PyTypeChecker
def test_enable_plans_missing_originating_cfg_raises():
    # covers: C000F023B0005
    p1 = strat.StrategyPlan("s", "iid", object, {}, (), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._enable_plans(plans=[p1], effective_cfg_by_iid={})
    assert "has no originating config mapping" in str(e.value)


# noinspection PyTypeChecker
def test_enable_plans_skips_disabled_and_enables_others_with_deps():
    # covers: C000F023B0002, C000F023B0004, C000F023B0006, C000F023B0007, C000F023B0008
    class C:
        precedence = 50

    p_disabled = strat.StrategyPlan("s", "d", C, {"x": 1}, (), 1)
    p_enabled = strat.StrategyPlan("s", "e", C, {"dep": strat.StrategyRef(strategy_name="d")}, ("z",), 1)

    effective = {
        "d": {"instance_id": "d", "criticality": StrategyCriticality.DISABLED},
        "e": {"instance_id": "e", "precedence": 3, "criticality": "required"},
    }
    enabled, crit = strat._enable_plans(plans=[p_disabled, p_enabled], effective_cfg_by_iid=effective)
    assert [p.instance_id for p in enabled] == ["e"]
    assert crit == {"e": StrategyCriticality.REQUIRED}
    assert enabled[0].depends_on == tuple(sorted({"z", "d"}))
    assert enabled[0].precedence == 3


# --------------------------------------------------------------------------------------
# _validate_enabled_dependencies_exist
# --------------------------------------------------------------------------------------

def test_validate_enabled_dependencies_exist_empty_list():
    # covers: C000F025B0001
    strat._validate_enabled_dependencies_exist([])


# noinspection PyTypeChecker
def test_validate_enabled_dependencies_exist_no_deps():
    # covers: C000F025B0002, C000F025B0003
    p = strat.StrategyPlan("s", "a", object, {}, (), 1)
    strat._validate_enabled_dependencies_exist([p])


# noinspection PyTypeChecker
def test_validate_enabled_dependencies_exist_missing_dep_raises():
    # covers: C000F025B0004, C000F025B0005
    p = strat.StrategyPlan("s", "a", object, {}, ("missing",), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._validate_enabled_dependencies_exist([p])
    assert "depends on missing or disabled" in str(e.value)


# noinspection PyTypeChecker
def test_validate_enabled_dependencies_exist_present_dep_ok():
    # covers: C000F025B0006
    a = strat.StrategyPlan("s", "a", object, {}, (), 1)
    b = strat.StrategyPlan("s", "b", object, {}, ("a",), 1)
    strat._validate_enabled_dependencies_exist([a, b])


# --------------------------------------------------------------------------------------
# _enforce_imperative_closure
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_enforce_imperative_closure_no_imperative_returns():
    # covers: C000F026B0001
    plans = [strat.StrategyPlan("s", "a", object, {}, (), 1, StrategyCriticality.OPTIONAL)]
    strat._enforce_imperative_closure(enabled_plans=plans, crit_by_iid={"a": StrategyCriticality.OPTIONAL})


# noinspection PyTypeChecker
def test_enforce_imperative_closure_root_has_no_deps():
    # covers: C000F026B0002, C000F026B0004, C000F026B0005
    plans = [strat.StrategyPlan("s", "a", object, {}, (), 1, StrategyCriticality.IMPERATIVE)]
    strat._enforce_imperative_closure(enabled_plans=plans, crit_by_iid={"a": StrategyCriticality.IMPERATIVE})


# noinspection PyTypeChecker
def test_enforce_imperative_closure_raises_for_non_imperative_dep():
    # covers: C000F026B0006, C000F026B0009
    a = strat.StrategyPlan("s", "a", object, {}, ("b",), 1, StrategyCriticality.IMPERATIVE)
    b = strat.StrategyPlan("s", "b", object, {}, (), 1, StrategyCriticality.OPTIONAL)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._enforce_imperative_closure(
            enabled_plans=[a, b],
            crit_by_iid={"a": StrategyCriticality.IMPERATIVE, "b": StrategyCriticality.OPTIONAL},
        )
    assert "depends on non IMPERATIVE" in str(e.value)


# noinspection PyTypeChecker
def test_enforce_imperative_closure_transitive_and_seen_dep_skips_duplicates():
    # covers: C000F026B0007, C000F026B0010, C000F026B0011, C000F026B0012
    root = strat.StrategyPlan("s", "root", object, {}, ("dep1", "dep2"), 1, StrategyCriticality.IMPERATIVE)
    dep1 = strat.StrategyPlan("s", "dep1", object, {}, (), 1, StrategyCriticality.IMPERATIVE)
    dep2 = strat.StrategyPlan("s", "dep2", object, {}, ("dep1",), 1, StrategyCriticality.IMPERATIVE)
    strat._enforce_imperative_closure(
        enabled_plans=[root, dep1, dep2],
        crit_by_iid={
            "root": StrategyCriticality.IMPERATIVE,
            "dep1": StrategyCriticality.IMPERATIVE,
            "dep2": StrategyCriticality.IMPERATIVE,
        },
    )


# --------------------------------------------------------------------------------------
# topo_sort_plans
# --------------------------------------------------------------------------------------

def test_topo_sort_plans_empty():
    # covers: C000F027B0001
    assert strat.topo_sort_plans([]) == []


# noinspection PyTypeChecker
def test_topo_sort_plans_unknown_dependency_raises():
    # covers: C000F027B0005
    p = strat.StrategyPlan("s", "a", object, {}, ("missing",), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.topo_sort_plans([p])
    assert "depends_on unknown" in str(e.value)


# noinspection PyTypeChecker
def test_topo_sort_plans_cycle_detected_raises():
    # covers: C000F027B0007, C000F027B0015
    a = strat.StrategyPlan("s", "a", object, {}, ("b",), 1)
    b = strat.StrategyPlan("s", "b", object, {}, ("a",), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.topo_sort_plans([a, b])
    assert "dependency cycle detected" in str(e.value)


# noinspection PyTypeChecker
def test_topo_sort_plans_orders_by_precedence_and_breaks_ties():
    # covers: C000F027B0002, C000F027B0004, C000F027B0006, C000F027B0008, C000F027B0010,
    #         C000F027B0011, C000F027B0012, C000F027B0013, C000F027B0014, C000F027B0016
    # Graph: A -> C, B -> C
    a = strat.StrategyPlan("s", "a", object, {}, (), 1)
    b = strat.StrategyPlan("s", "b", object, {}, (), 2)
    c = strat.StrategyPlan("s", "c", object, {}, ("a", "b"), 3)
    ordered = strat.topo_sort_plans([c, b, a])  # intentionally shuffled input
    assert [p.instance_id for p in ordered] == ["a", "b", "c"]


# --------------------------------------------------------------------------------------
# _validate_ctor_kwargs
# --------------------------------------------------------------------------------------

class _AcceptsKw:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _NoKw:
    def __init__(self, a, b=1):
        self.a = a
        self.b = b


# noinspection PyTypeChecker
def test_validate_ctor_kwargs_accepts_kwargs():
    # covers: C000F028B0001
    strat._validate_ctor_kwargs(strategy_cls=_AcceptsKw, ctor_kwargs={"x": 1}, ctx="ctx")


# noinspection PyTypeChecker
def test_validate_ctor_kwargs_rejects_extra_kwargs():
    # covers: C000F028B0002, C000F028B0004
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._validate_ctor_kwargs(strategy_cls=_NoKw, ctor_kwargs={"a": 1, "extra": 2}, ctx="ctx")
    assert "ctor does not accept kwargs" in str(e.value)


# noinspection PyTypeChecker
def test_validate_ctor_kwargs_allows_only_allowed_keys():
    # covers: C000F028B0002, C000F028B0003
    strat._validate_ctor_kwargs(strategy_cls=_NoKw, ctor_kwargs={"a": 1, "b": 2}, ctx="ctx")


# --------------------------------------------------------------------------------------
# _resolve_ctor_kwargs
# --------------------------------------------------------------------------------------

def test_resolve_ctor_kwargs_empty():
    # covers: C000F029B0001
    assert strat._resolve_ctor_kwargs({}, {}) == {}


def test_resolve_ctor_kwargs_strategyref_missing_registry_raises():
    # covers: C000F029B0002, C000F029N001B0001
    kw = {"dep": strat.StrategyRef(strategy_name="a")}
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._resolve_ctor_kwargs(kw, {})
    assert "was not instantiated before injection" in str(e.value)


def test_resolve_ctor_kwargs_nested_types_and_registry_hits():
    # covers: C000F029N001B0002..B0006
    reg = {"a": object()}
    kw = {
        "m": {"x": strat.StrategyRef(strategy_name="a")},
        "l": [strat.StrategyRef(strategy_name="a")],
        "t": (strat.StrategyRef(strategy_name="a"),),
        "p": 5,
    }
    out = strat._resolve_ctor_kwargs(kw, reg)
    assert out["m"]["x"] is reg["a"]
    assert out["l"][0] is reg["a"]
    assert out["t"][0] is reg["a"]
    assert out["p"] == 5


# --------------------------------------------------------------------------------------
# _apply_plan_metadata
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_apply_plan_metadata_no_attrs_is_noop():
    # covers: C000F030N001B0001
    class NoAttrs:
        pass

    inst = NoAttrs()
    plan = strat.StrategyPlan("s", "iid", object, {}, (), 1, StrategyCriticality.REQUIRED)
    strat._apply_plan_metadata(inst=inst, plan=plan, ctx="ctx")  # should not raise


# noinspection PyTypeChecker
def test_apply_plan_metadata_attrs_already_match_is_noop():
    # covers: C000F030N001B0002, C000F030N001B0003
    class HasAttrs:
        def __init__(self):
            self.instance_id = "iid"
            self.precedence = 1
            self.criticality = StrategyCriticality.REQUIRED

    inst = HasAttrs()
    plan = strat.StrategyPlan("s", "iid", object, {}, (), 1, StrategyCriticality.REQUIRED)
    strat._apply_plan_metadata(inst=inst, plan=plan, ctx="ctx")
    assert inst.instance_id == "iid"


# noinspection PyTypeChecker
def test_apply_plan_metadata_sets_attrs_when_different():
    # covers: C000F030N001B0004, C000F030N001B0005
    class HasAttrs:
        def __init__(self):
            self.instance_id = "old"
            self.precedence = 999
            self.criticality = StrategyCriticality.OPTIONAL

    inst = HasAttrs()
    plan = strat.StrategyPlan("s", "iid", object, {}, (), 1, StrategyCriticality.REQUIRED)
    strat._apply_plan_metadata(inst=inst, plan=plan, ctx="ctx")
    assert inst.instance_id == "iid"
    assert inst.precedence == 1
    assert inst.criticality == StrategyCriticality.REQUIRED


# noinspection PyTypeChecker
def test_apply_plan_metadata_raises_if_cannot_set_attr():
    # covers: C000F030N001B0006
    class ReadOnly:
        @property
        def instance_id(self):
            return "old"

    inst = ReadOnly()
    plan = strat.StrategyPlan("s", "iid", object, {}, (), 1, StrategyCriticality.REQUIRED)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat._apply_plan_metadata(inst=inst, plan=plan, ctx="ctx")
    assert "could not set instance_id" in str(e.value)


# --------------------------------------------------------------------------------------
# instantiate_plans
# --------------------------------------------------------------------------------------

def test_instantiate_plans_empty():
    # covers: C000F031B0001
    assert strat.instantiate_plans([]) == []


# noinspection PyTypeChecker
def test_instantiate_plans_validate_ctor_kwargs_error_propagates():
    # covers: C000F031B0002, C000F031B0003
    plan = strat.StrategyPlan(
        strategy_name="s",
        instance_id="iid",
        strategy_cls=_NoKw,
        ctor_kwargs={"a": 1, "extra": 2},
        depends_on=(),
        precedence=1,
    )
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.instantiate_plans([plan])
    assert "ctor does not accept kwargs" in str(e.value)


# noinspection PyTypeChecker
def test_instantiate_plans_constructor_exception_propagates():
    # covers: C000F031B0004
    class Boom:
        def __init__(self, **kwargs):
            raise RuntimeError("boom")

    plan = strat.StrategyPlan("s", "iid", Boom, {}, (), 1)
    with pytest.raises(RuntimeError) as e:
        strat.instantiate_plans([plan])
    assert "boom" in str(e.value)


# noinspection PyTypeChecker
def test_instantiate_plans_instance_id_mismatch_raises():
    # covers: C000F031B0005
    class NoInstanceIdAttr:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    plan = strat.StrategyPlan("s", "iid", NoInstanceIdAttr, {}, (), 1)
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.instantiate_plans([plan])
    assert "does not match planned instance_id" in str(e.value)


# noinspection PyTypeChecker
def test_instantiate_plans_success_with_dependency_injection():
    # covers: C000F031B0006
    class Dep:
        def __init__(self, **kwargs):
            self.instance_id = "dep"

    class User:
        def __init__(self, dep):
            self.dep = dep
            self.instance_id = "user"

    dep_plan = strat.StrategyPlan("dep", "dep", Dep, {}, (), 1)
    user_plan = strat.StrategyPlan("user", "user", User, {"dep": strat.StrategyRef(instance_id="dep")}, ("dep",), 2)

    out = strat.instantiate_plans([dep_plan, user_plan])
    assert len(out) == 2
    assert out[1].dep is out[0]
    assert getattr(out[0], "instance_id") == "dep"
    assert getattr(out[1], "instance_id") == "user"


# --------------------------------------------------------------------------------------
# load_strategies
# --------------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_load_strategies_uses_empty_config_specs_when_no_config_packages(monkeypatch):
    # covers: C000F032B0002, C000F032B0004
    monkeypatch.setattr(
        strat,
        "discover_strategy_classes",
        lambda **kw: {"s": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")},
    )
    monkeypatch.setattr(strat, "build_strategy_plans", lambda **kw: [])
    monkeypatch.setattr(strat, "topo_sort_plans", lambda plans: plans)
    monkeypatch.setattr(strat, "instantiate_plans", lambda plans: ["ok"])

    out = strat.load_strategies(strategy_package="p", strategy_entrypoint_group="g")
    assert out == ["ok"]


# noinspection PyTypeChecker
def test_load_strategies_calls_discover_config_specs_when_config_packages_present(monkeypatch):
    # covers: C000F032B0001
    called = {"cfg": 0}
    monkeypatch.setattr(
        strat,
        "discover_strategy_classes",
        lambda **kw: {"s": strat._StrategyClassInfo(strategy_cls=object, origin="builtin")},
    )
    monkeypatch.setattr(
        strat,
        "discover_config_specs",
        lambda **kw: called.__setitem__("cfg", called["cfg"] + 1) or {},
    )
    monkeypatch.setattr(strat, "build_strategy_plans", lambda **kw: [])
    monkeypatch.setattr(strat, "topo_sort_plans", lambda plans: plans)
    monkeypatch.setattr(strat, "instantiate_plans", lambda plans: ["ok"])

    strat.load_strategies(strategy_package="p", strategy_entrypoint_group="g", builtin_config_package="bp")
    assert called["cfg"] == 1


def test_load_strategies_propagates_strategy_config_error(monkeypatch):
    # covers: C000F032B0003
    monkeypatch.setattr(strat, "discover_strategy_classes", lambda **kw: {})
    monkeypatch.setattr(
        strat,
        "build_strategy_plans",
        lambda **kw: (_ for _ in ()).throw(strat.StrategyConfigError("nope")),
    )
    with pytest.raises(strat.StrategyConfigError) as e:
        strat.load_strategies(strategy_package="p", strategy_entrypoint_group="g")
    assert "nope" in str(e.value)
