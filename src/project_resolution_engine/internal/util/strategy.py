from __future__ import annotations

import importlib
import inspect
import pkgutil
from abc import ABC
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence, Iterable
from dataclasses import dataclass
from importlib.metadata import entry_points, EntryPoint
from typing import Any, TypeVar, Generic

from project_resolution_engine.strategies import (
    BaseArtifactResolutionStrategy,
    InstantiationPolicy,
    StrategyCriticality,
    ResolutionStrategyConfig,
)

ArtifactStrategyType = TypeVar(
    "ArtifactStrategyType", bound="BaseArtifactResolutionStrategy"
)
T = TypeVar("T")


class StrategyConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StrategyRef:
    """
    Dependency injection reference to an already planned strategy instance.

    normalized_instance_id must resolve to a concrete instance_id that exists in the plan set.
    """

    strategy_name: str = ""
    instance_id: str = ""

    def normalized_instance_id(self) -> str:
        iid = self.instance_id or self.strategy_name
        if not iid:
            raise StrategyConfigError(
                "StrategyRef requires strategy_name or instance_id"
            )
        return iid


@dataclass(frozen=True, slots=True)
class StrategyPlan:
    """
    A plan to instantiate a strategy instance.

    ctor_kwargs may contain StrategyRef values; they are replaced with actual instances
    during instantiation. depends_on must contain instance_id values.
    """

    strategy_name: str
    instance_id: str
    strategy_cls: type[BaseArtifactResolutionStrategy]
    ctor_kwargs: Mapping[str, Any]
    depends_on: tuple[str, ...]
    precedence: int
    criticality: StrategyCriticality = StrategyCriticality.OPTIONAL


class BaseArtifactResolutionStrategyConfig(Generic[ArtifactStrategyType], ABC):
    """
    Base class for config specs.

    A config spec binds raw config to a concrete instantiation plan.

    Defaults:
      - SINGLETON strategies should plan exactly one instance with instance_id == strategy_name.
      - PROTOTYPE strategies may plan one or more instances.
    """

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return {}

    @classmethod
    def plan(
        cls,
        *,
        strategy_cls: type[BaseArtifactResolutionStrategy],
        config: Mapping[str, Any],
    ) -> list[StrategyPlan]:
        raise NotImplementedError


StrategyCls = type[BaseArtifactResolutionStrategy[Any]]
ConfigSpecCls = type[BaseArtifactResolutionStrategyConfig[Any]]


class DefaultStrategyConfig(BaseArtifactResolutionStrategyConfig, ABC):
    @classmethod
    def plan(
        cls,
        *,
        strategy_cls: type[BaseArtifactResolutionStrategy],
        config: Mapping[str, Any],
    ) -> list[StrategyPlan]:
        # Use config binding first; fall back to discovery only when missing.
        strategy_name = config.get("strategy_name") or _strategy_name_for_class(
            strategy_cls
        )
        if not isinstance(strategy_name, str) or not strategy_name:
            raise StrategyConfigError("strategy_name must be a non-empty string")

        instance_id = config.get("instance_id") or strategy_name
        if not isinstance(instance_id, str) or not instance_id:
            raise StrategyConfigError("instance_id must be a non-empty string")

        precedence = config.get("precedence", getattr(strategy_cls, "precedence", 100))
        if not isinstance(precedence, int):
            raise StrategyConfigError(
                f"precedence: expected int, got {type(precedence).__name__}"
            )

        # Only forward *strategy-specific* keys here.
        ctor_kwargs = dict(config)
        ctor_kwargs.pop("strategy_name", None)
        ctor_kwargs.pop("instance_id", None)
        ctor_kwargs.pop("precedence", None)
        ctor_kwargs.pop("criticality", None)

        return [
            StrategyPlan(
                strategy_name=strategy_name,
                instance_id=instance_id,
                strategy_cls=strategy_cls,
                ctor_kwargs=ctor_kwargs,
                depends_on=(),  # planner will scan ctor_kwargs for StrategyRef deps
                precedence=precedence,
            )
        ]


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _StrategyClassInfo:
    strategy_cls: type[BaseArtifactResolutionStrategy]
    origin: str  # "builtin" | "entrypoint"


@dataclass(frozen=True, slots=True)
class _IngestedConfigs:
    cfg_by_instance_id: dict[str, dict[str, Any]]
    bound_iids_by_strategy: dict[str, list[str]]


def _iter_module_objects(package_name: str) -> Iterable[Any]:
    if not package_name:
        yield from ()
    package = importlib.import_module(package_name)
    for _finder, mod_name, _ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        module = importlib.import_module(mod_name)
        yield from vars(module).values()
    return None


def _iter_entrypoint_objects(group: str) -> Iterable[Any]:
    if not group:
        yield from ()
    ep: EntryPoint
    for ep in entry_points().select(group=group):
        yield ep.load()
    return None


def _builtin_strategy_classes(
    package_name: str,
) -> list[type[BaseArtifactResolutionStrategy[Any]]]:
    out: list[type[BaseArtifactResolutionStrategy[Any]]] = []
    for obj in _iter_module_objects(package_name):
        if inspect.isclass(obj) and issubclass(obj, BaseArtifactResolutionStrategy):
            out.append(obj)
    return out


def _entrypoint_strategy_classes(
    group: str,
) -> list[type[BaseArtifactResolutionStrategy[Any]]]:
    out: list[type[BaseArtifactResolutionStrategy[Any]]] = []
    for obj in _iter_entrypoint_objects(group):
        if inspect.isclass(obj) and issubclass(obj, BaseArtifactResolutionStrategy):
            out.append(obj)
    return out


def _builtin_config_spec_classes(
    package_name: str,
) -> list[type[BaseArtifactResolutionStrategyConfig[Any]]]:
    out: list[type[BaseArtifactResolutionStrategyConfig[Any]]] = []
    for obj in _iter_module_objects(package_name):
        if inspect.isclass(obj) and issubclass(
            obj, BaseArtifactResolutionStrategyConfig
        ):
            out.append(obj)
    return out


def _entrypoint_config_spec_classes(
    group: str,
) -> list[type[BaseArtifactResolutionStrategyConfig[Any]]]:
    out: list[type[BaseArtifactResolutionStrategyConfig[Any]]] = []
    for obj in _iter_entrypoint_objects(group):
        if inspect.isclass(obj) and issubclass(
            obj, BaseArtifactResolutionStrategyConfig
        ):
            out.append(obj)
    return out


def _strategy_name_for_class(strategy_cls: type[BaseArtifactResolutionStrategy]) -> str:
    # Preferred: explicit class attribute identifying the strategy type.
    name = getattr(strategy_cls, "strategy_name", None)
    if isinstance(name, str) and name:
        return name

    # Secondary: some code uses "name" as a class attr; accept if present.
    name2 = getattr(strategy_cls, "name", None)
    if isinstance(name2, str) and name2:
        return name2

    return strategy_cls.__name__


def discover_strategy_classes(
    *, strategy_package: str, strategy_entrypoint_group: str
) -> dict[str, _StrategyClassInfo]:
    """
    Returns mapping strategy_name -> class info.

    Duplicate strategy_name across builtin/entrypoint is an error.
    """
    by_name: dict[str, _StrategyClassInfo] = {}

    for cls in _builtin_strategy_classes(strategy_package):
        name = _strategy_name_for_class(cls)
        if name in by_name:
            raise StrategyConfigError(f"duplicate strategy_name discovered: '{name}'")
        by_name[name] = _StrategyClassInfo(strategy_cls=cls, origin="builtin")

    for cls in _entrypoint_strategy_classes(strategy_entrypoint_group):
        name = _strategy_name_for_class(cls)
        if name in by_name:
            raise StrategyConfigError(f"duplicate strategy_name discovered: '{name}'")
        by_name[name] = _StrategyClassInfo(strategy_cls=cls, origin="entrypoint")

    return by_name


def discover_config_specs(
    *, builtin_config_package: str, config_entrypoint_group: str
) -> dict[str, type]:
    """
    Returns mapping strategy_name -> config spec class.

    Config spec classes must declare class attr: strategy_name = "<name>".
    Duplicate strategy_name is an error.
    """
    classes = _builtin_config_spec_classes(
        builtin_config_package
    ) + _entrypoint_config_spec_classes(config_entrypoint_group)
    by_strategy_name: dict[str, type] = {}

    for cls in classes:
        strategy_name = getattr(cls, "strategy_name", None)
        if not (isinstance(strategy_name, str) and strategy_name):
            continue
        if strategy_name in by_strategy_name:
            raise StrategyConfigError(
                f"duplicate config spec for strategy_name '{strategy_name}'"
            )
        by_strategy_name[strategy_name] = cls

    return by_strategy_name


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #


def _ensure_dict(cfg: Mapping[str, Any]) -> dict[str, Any]:
    return dict(cfg)


def _effective_precedence(
    *,
    cfg: Mapping[str, Any],
    strategy_cls: type[BaseArtifactResolutionStrategy],
    fallback: int,
) -> int:
    if "precedence" in cfg:
        v = cfg["precedence"]
        if not isinstance(v, int):
            raise StrategyConfigError(
                f"precedence: expected int, got {type(v).__name__}"
            )
        return v
    v2 = getattr(strategy_cls, "precedence", fallback)
    if not isinstance(v2, int):
        return fallback
    return v2


def _effective_criticality(
    *, cfg: Mapping[str, Any], strategy_cls: type[BaseArtifactResolutionStrategy]
) -> StrategyCriticality:
    if "criticality" in cfg:
        v = cfg["criticality"]
        if isinstance(v, StrategyCriticality):
            return v
        if isinstance(v, str):
            try:
                return StrategyCriticality(v)
            except ValueError as e:
                raise StrategyConfigError(f"criticality: invalid value '{v}'") from e
        raise StrategyConfigError(
            f"criticality: expected StrategyCriticality or str, got {type(v).__name__}"
        )
    v2 = getattr(strategy_cls, "criticality", StrategyCriticality.OPTIONAL)
    if isinstance(v2, StrategyCriticality):
        return v2
    if isinstance(v2, str):
        try:
            return StrategyCriticality(v2)
        except ValueError:
            return StrategyCriticality.OPTIONAL
    return StrategyCriticality.OPTIONAL


# :: UtilityOperation | type=configuration
def _scan_deps(val: Any, out: set[str]) -> None:
    if isinstance(val, StrategyRef):
        sr: StrategyRef = val
        out.add(sr.normalized_instance_id())
        return
    if isinstance(val, Mapping):
        m: Mapping = val
        for v in m.values():
            _scan_deps(v, out)
        return
    if isinstance(val, (list, tuple)):
        for v in val:
            _scan_deps(v, out)
        return


def build_strategy_plans(
    *,
    strategy_classes: Mapping[str, _StrategyClassInfo],
    config_specs: Mapping[str, type[BaseArtifactResolutionStrategyConfig]],
    raw_configs_by_instance_id: Mapping[str, ResolutionStrategyConfig] | None,
) -> list[StrategyPlan]:
    """
    Bind configs to discovered strategy types and produce instantiation plans.

    Rules:
      - Builtins: instantiate one singleton instance by default unless DISABLED.
      - Entrypoints: instantiate only if a config binds to the strategy.
      - SINGLETON: must have exactly one instance_id == strategy_name.
      - PROTOTYPE: may have one or more instances (unique instance_id).
    """
    ingested = _ingest_raw_configs(
        raw_configs_by_instance_id=raw_configs_by_instance_id,
        strategy_classes=strategy_classes,
    )

    plans, effective_cfg_by_iid = _plan_all_strategies(
        strategy_classes=strategy_classes,
        config_specs=config_specs,
        cfg_by_instance_id=ingested.cfg_by_instance_id,
        bound_iids_by_strategy=ingested.bound_iids_by_strategy,
    )
    if not plans:
        return []

    enabled_plans, crit_by_iid = _enable_plans(
        plans=plans, effective_cfg_by_iid=effective_cfg_by_iid
    )
    if not enabled_plans:
        return []

    _validate_enabled_dependencies_exist(enabled_plans)

    _enforce_imperative_closure(enabled_plans=enabled_plans, crit_by_iid=crit_by_iid)

    return enabled_plans


def _ingest_raw_configs(
    *,
    raw_configs_by_instance_id: Mapping[str, ResolutionStrategyConfig] | None,
    strategy_classes: Mapping[str, _StrategyClassInfo],
) -> _IngestedConfigs:
    raw_configs_by_instance_id = raw_configs_by_instance_id or {}

    cfg_by_instance_id: dict[str, dict[str, Any]] = {}
    bound_iids_by_strategy: dict[str, list[str]] = defaultdict(list)

    for iid, raw_cfg in raw_configs_by_instance_id.items():
        _validate_instance_id_key(iid)
        _validate_raw_cfg_mapping(iid, raw_cfg)

        cfg = _ensure_dict(raw_cfg)

        _validate_or_set_cfg_instance_id(iid, cfg)

        strategy_name = _normalize_and_validate_strategy_name(
            iid=iid, cfg=cfg, strategy_classes=strategy_classes
        )
        cfg["strategy_name"] = strategy_name

        cfg_by_instance_id[iid] = cfg
        bound_iids_by_strategy[strategy_name].append(iid)

    return _IngestedConfigs(
        cfg_by_instance_id=cfg_by_instance_id,
        bound_iids_by_strategy=dict(bound_iids_by_strategy),
    )


def _validate_instance_id_key(iid: Any) -> None:
    if not isinstance(iid, str) or not iid:
        raise StrategyConfigError(
            "strategy config keys must be non empty strings (instance_id)"
        )


def _validate_raw_cfg_mapping(iid: str, raw_cfg: Any) -> None:
    if not isinstance(raw_cfg, Mapping):
        raise StrategyConfigError(f"config for instance_id '{iid}' must be a mapping")


def _validate_or_set_cfg_instance_id(iid: str, cfg: dict[str, Any]) -> None:
    if "instance_id" in cfg and cfg["instance_id"] != iid:
        raise StrategyConfigError(
            f"config instance_id mismatch for key '{iid}': cfg['instance_id']={cfg['instance_id']!r}"
        )
    cfg["instance_id"] = iid


def _normalize_and_validate_strategy_name(
    *, iid: str, cfg: dict[str, Any], strategy_classes: Mapping[str, _StrategyClassInfo]
) -> str:
    strategy_name = cfg.get("strategy_name")
    if strategy_name is None:
        strategy_name = iid

    if not isinstance(strategy_name, str) or not strategy_name:
        raise StrategyConfigError(
            f"strategy_name for instance_id '{iid}' must be a non empty string"
        )

    if strategy_name not in strategy_classes:
        raise StrategyConfigError(
            f"unknown strategy_name '{strategy_name}' for instance_id '{iid}' (not discovered)"
        )

    return strategy_name


def _plan_all_strategies(
    *,
    strategy_classes: Mapping[str, _StrategyClassInfo],
    config_specs: Mapping[str, type[BaseArtifactResolutionStrategyConfig]],
    cfg_by_instance_id: Mapping[str, dict[str, Any]],
    bound_iids_by_strategy: Mapping[str, list[str]],
) -> tuple[list[StrategyPlan], dict[str, dict[str, Any]]]:
    plans: list[StrategyPlan] = []
    defaults_cfg_by_iid: dict[str, dict[str, Any]] = {}
    effective_cfg_by_iid: dict[str, dict[str, Any]] = {}

    for strategy_name, info in strategy_classes.items():
        strategy_cls = info.strategy_cls
        spec_cls: type[BaseArtifactResolutionStrategyConfig] = config_specs.get(
            strategy_name, DefaultStrategyConfig
        )
        policy = getattr(
            strategy_cls, "instantiation_policy", InstantiationPolicy.SINGLETON
        )

        iids = list(bound_iids_by_strategy.get(strategy_name, []))

        iids = _select_instance_ids_for_strategy(
            strategy_name=strategy_name,
            info=info,
            iids=iids,
            spec_cls=spec_cls,
            defaults_cfg_by_iid=defaults_cfg_by_iid,
        )

        _enforce_singleton_policy(strategy_name=strategy_name, policy=policy, iids=iids)

        for iid in iids:
            raw = cfg_by_instance_id.get(iid) or defaults_cfg_by_iid.get(iid)
            if raw is None:
                raise StrategyConfigError(
                    f"internal error: missing config for planned instance_id '{iid}'"
                )

            merged = dict(spec_cls.defaults())
            merged.update(raw)
            merged["strategy_name"] = strategy_name
            merged["instance_id"] = iid
            effective_cfg_by_iid[iid] = merged
            planned = spec_cls.plan(strategy_cls=strategy_cls, config=merged)
            plans.extend(planned)

    return plans, effective_cfg_by_iid


def _select_instance_ids_for_strategy(
    *,
    strategy_name: str,
    info: _StrategyClassInfo,
    iids: list[str],
    spec_cls: type[BaseArtifactResolutionStrategyConfig],
    defaults_cfg_by_iid: dict[str, dict[str, Any]],
) -> list[str]:
    if info.origin == "entrypoint":
        if not iids:
            return []
        return iids

    # builtin
    if not iids:
        cfg = dict(spec_cls.defaults())
        cfg["strategy_name"] = strategy_name
        cfg["instance_id"] = strategy_name
        defaults_cfg_by_iid[strategy_name] = cfg
        return [strategy_name]

    return iids


def _enforce_singleton_policy(
    *, strategy_name: str, policy: Any, iids: list[str]
) -> None:
    if policy is InstantiationPolicy.SINGLETON:
        if len(iids) != 1:
            raise StrategyConfigError(
                f"strategy '{strategy_name}' is SINGLETON but {len(iids)} instances were configured: {iids}"
            )
        if iids[0] != strategy_name:
            raise StrategyConfigError(
                f"strategy '{strategy_name}' is SINGLETON but instance_id '{iids[0]}' != strategy_name"
            )


def _enable_plans(
    *, plans: list[StrategyPlan], effective_cfg_by_iid: Mapping[str, dict[str, Any]]
) -> tuple[list[StrategyPlan], dict[str, StrategyCriticality]]:
    seen: set[str] = set()
    enabled_plans: list[StrategyPlan] = []
    crit_by_iid: dict[str, StrategyCriticality] = {}

    for plan in plans:
        if plan.instance_id in seen:
            raise StrategyConfigError(
                f"duplicate instance_id planned: '{plan.instance_id}'"
            )
        seen.add(plan.instance_id)

        merged_cfg = effective_cfg_by_iid.get(plan.instance_id)
        if merged_cfg is None:
            raise StrategyConfigError(
                f"planned instance_id '{plan.instance_id}' has no originating config mapping"
            )

        precedence = _effective_precedence(
            cfg=merged_cfg, strategy_cls=plan.strategy_cls, fallback=plan.precedence
        )
        criticality = _effective_criticality(
            cfg=merged_cfg, strategy_cls=plan.strategy_cls
        )

        if criticality is StrategyCriticality.DISABLED:
            continue

        ctor_kwargs = _strip_planner_keys(plan.ctor_kwargs)
        deps: set[str] = set(plan.depends_on)
        _scan_deps(ctor_kwargs, deps)
        crit_by_iid[plan.instance_id] = criticality

        enabled_plans.append(
            StrategyPlan(
                strategy_name=plan.strategy_name,
                instance_id=plan.instance_id,
                strategy_cls=plan.strategy_cls,
                ctor_kwargs=ctor_kwargs,
                depends_on=tuple(sorted(deps)),
                precedence=precedence,
                criticality=criticality,
            )
        )

    return enabled_plans, crit_by_iid


def _strip_planner_keys(ctor_kwargs: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(ctor_kwargs)
    out.pop("strategy_name", None)
    out.pop("instance_id", None)
    out.pop("precedence", None)
    out.pop("criticality", None)
    return out


def _validate_enabled_dependencies_exist(enabled_plans: list[StrategyPlan]) -> None:
    enabled_ids = {p.instance_id for p in enabled_plans}
    for p in enabled_plans:
        for dep in p.depends_on:
            if dep not in enabled_ids:
                raise StrategyConfigError(
                    f"strategy instance '{p.instance_id}' depends on missing or disabled instance '{dep}'"
                )


def _enforce_imperative_closure(
    *, enabled_plans: list[StrategyPlan], crit_by_iid: Mapping[str, StrategyCriticality]
) -> None:
    imperative = {
        iid for iid, c in crit_by_iid.items() if c is StrategyCriticality.IMPERATIVE
    }
    if not imperative:
        return

    deps_by_iid = {p.instance_id: set(p.depends_on) for p in enabled_plans}

    for root in imperative:
        stack = list(deps_by_iid[root])
        seen_dep: set[str] = set()

        while stack:
            dep = stack.pop()
            if dep in seen_dep:
                continue
            seen_dep.add(dep)

            if crit_by_iid.get(dep) is not StrategyCriticality.IMPERATIVE:
                raise StrategyConfigError(
                    f"IMPERATIVE instance '{root}' depends on non IMPERATIVE instance '{dep}'. "
                    f"Set '{dep}' criticality to IMPERATIVE or disable '{root}'."
                )

            stack.extend(deps_by_iid.get(dep, ()))


# --------------------------------------------------------------------------- #
# Topological sort
# --------------------------------------------------------------------------- #


def _build_dependency_graph(
    plans: Sequence[StrategyPlan], by_id: dict[str, StrategyPlan]
) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Build out-edges and in-degree maps for the dependency graph."""
    out_edges: dict[str, set[str]] = {p.instance_id: set() for p in plans}
    in_degree: dict[str, int] = {p.instance_id: 0 for p in plans}

    for p in plans:
        for dep in p.depends_on:
            if dep not in by_id:
                raise StrategyConfigError(
                    f"{p.instance_id}: depends_on unknown instance_id '{dep}'"
                )
            out_edges[dep].add(p.instance_id)
            in_degree[p.instance_id] += 1

    return out_edges, in_degree


def _initialize_ready_queue(
    plans: Sequence[StrategyPlan],
    in_degree: dict[str, int],
    by_id: dict[str, StrategyPlan],
) -> deque[str]:
    """Find nodes with no dependencies and create initial queue."""
    ready: list[str] = [iid for iid, deg in in_degree.items() if deg == 0]
    ready.sort(key=lambda iid: (by_id[iid].precedence, iid))
    return deque(ready)


def _process_topological_order(
    queue: deque[str],
    by_id: dict[str, StrategyPlan],
    out_edges: dict[str, set[str]],
    in_degree: dict[str, int],
) -> list[StrategyPlan]:
    """Process queue in topological order, maintaining stable sort."""
    ordered: list[StrategyPlan] = []

    while queue:
        iid = queue.popleft()
        ordered.append(by_id[iid])

        for nxt in sorted(out_edges[iid], key=lambda x: (by_id[x].precedence, x)):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    return ordered


def _validate_no_cycles(
    ordered: list[StrategyPlan],
    plans: Sequence[StrategyPlan],
    in_degree: dict[str, int],
) -> None:
    """Ensure all nodes were processed (no cycles exist)."""
    if len(ordered) != len(plans):
        remaining = [iid for iid, deg in in_degree.items() if deg > 0]
        raise StrategyConfigError(f"dependency cycle detected among: {remaining}")


def topo_sort_plans(plans: Sequence[StrategyPlan]) -> list[StrategyPlan]:
    """
    Stable Kahn topo-sort.

    When multiple nodes are available, order by (precedence, instance_id) for determinism.
    """
    by_id = {p.instance_id: p for p in plans}
    out_edges, in_degree = _build_dependency_graph(plans, by_id)
    ready_queue = _initialize_ready_queue(plans, in_degree, by_id)
    ordered = _process_topological_order(ready_queue, by_id, out_edges, in_degree)
    _validate_no_cycles(ordered, plans, in_degree)
    return ordered


# --------------------------------------------------------------------------- #
# Instantiation
# --------------------------------------------------------------------------- #


def _validate_ctor_kwargs(
    *,
    strategy_cls: type[BaseArtifactResolutionStrategy],
    ctor_kwargs: Mapping[str, Any],
    ctx: str,
) -> None:
    """
    Validate that ctor_kwargs can be passed to strategy_cls(...) deterministically.

    If the strategy constructor accepts **kwargs, allow anything.
    Otherwise require all keys to be accepted parameters.
    """
    sig = inspect.signature(strategy_cls)
    params = sig.parameters.values()
    accepts_kwargs = any(p.kind is p.VAR_KEYWORD for p in params)
    if accepts_kwargs:
        return
    allowed = {p.name for p in params}
    extra = [k for k in ctor_kwargs.keys() if k not in allowed]
    if extra:
        raise StrategyConfigError(f"{ctx}: ctor does not accept kwargs: {extra}")


def _resolve_ctor_kwargs(
    ctor_kwargs: Mapping[str, Any], registry: Mapping[str, Any]
) -> dict[str, Any]:
    def _resolve(val: Any) -> Any:
        if isinstance(val, StrategyRef):
            sr: StrategyRef = val
            iid = sr.normalized_instance_id()
            if iid not in registry:
                raise StrategyConfigError(
                    f"dependency '{iid}' was not instantiated before injection"
                )
            return registry[iid]
        if isinstance(val, Mapping):
            m: Mapping = val
            return {k: _resolve(m) for k, v in m.items()}
        if isinstance(val, list):
            return [_resolve(v) for v in val]
        if isinstance(val, tuple):
            return tuple(_resolve(v) for v in val)
        return val

    return {k: _resolve(v) for k, v in ctor_kwargs.items()}


def _apply_plan_metadata(*, inst: Any, plan: StrategyPlan, ctx: str) -> None:
    """
    Apply planner metadata to the instance without making it part of ctor kwargs.

    If the attribute exists and cannot be set, that's an error because the plan
    requires these values to be coherent.
    """

    def _set_attr(name: str, value: Any) -> None:
        if not hasattr(inst, name):
            return
        cur = getattr(inst, name, None)
        if cur == value:
            return
        try:
            object.__setattr__(inst, name, value)
        except Exception as e:
            raise StrategyConfigError(f"{ctx}: could not set {name}") from e

    _set_attr("instance_id", plan.instance_id)
    _set_attr("precedence", plan.precedence)
    _set_attr("criticality", plan.criticality)


def instantiate_plans(plans: Sequence[StrategyPlan]) -> list:
    """
    Instantiate strategy instances from StrategyPlan entries.
    """
    registry: dict[str, Any] = {}
    instances: list = []

    for plan in plans:
        resolved_kwargs = _resolve_ctor_kwargs(plan.ctor_kwargs, registry)
        ctx = f"strategy={plan.strategy_name} instance_id={plan.instance_id}"

        call_kwargs = dict(resolved_kwargs)
        call_kwargs.pop("strategy_name", None)
        call_kwargs.pop("instance_id", None)
        call_kwargs.pop("precedence", None)
        call_kwargs.pop("criticality", None)

        _validate_ctor_kwargs(
            strategy_cls=plan.strategy_cls, ctor_kwargs=call_kwargs, ctx=ctx
        )

        inst = plan.strategy_cls(**call_kwargs)

        _apply_plan_metadata(inst=inst, plan=plan, ctx=ctx)

        if getattr(inst, "instance_id", None) != plan.instance_id:
            raise StrategyConfigError(
                f"{ctx}: constructed instance_id '{getattr(inst, 'instance_id', None)}' "
                f"does not match planned instance_id '{plan.instance_id}'"
            )

        registry[plan.instance_id] = inst
        instances.append(inst)

    return instances


# --------------------------------------------------------------------------- #
# Public loader
# --------------------------------------------------------------------------- #


# :: MechanicalOperation | type=configuration
def load_strategies(
    *,
    strategy_package: str,
    strategy_entrypoint_group: str,
    builtin_config_package: str = "",
    config_entrypoint_group: str = "",
    raw_configs_by_instance_id: Mapping[str, ResolutionStrategyConfig] | None = None,
) -> list:
    """
    Discover -> plan -> topo sort -> instantiate.

    raw_configs_by_instance_id is keyed by instance_id and binds to strategy types via:
      - cfg['strategy_name'] if present
      - else strategy_name := instance_id
    """
    strategy_classes = discover_strategy_classes(
        strategy_package=strategy_package,
        strategy_entrypoint_group=strategy_entrypoint_group,
    )

    config_specs = (
        discover_config_specs(
            builtin_config_package=builtin_config_package,
            config_entrypoint_group=config_entrypoint_group,
        )
        if (builtin_config_package or config_entrypoint_group)
        else {}
    )

    plans = build_strategy_plans(
        strategy_classes=strategy_classes,
        config_specs=config_specs,
        raw_configs_by_instance_id=raw_configs_by_instance_id,
    )

    ordered = topo_sort_plans(plans)
    return instantiate_plans(ordered)
