from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from project_resolution_engine.internal.builtin_strategies import (
    DirectUriCoreMetadataStrategy,
    DirectUriWheelFileStrategy,
    HttpWheelFileStrategy,
    Pep658CoreMetadataHttpStrategy,
    Pep691IndexMetadataHttpStrategy,
    WheelExtractedCoreMetadataStrategy,
)
from project_resolution_engine.internal.util.strategy import (
    BaseArtifactResolutionStrategyConfig,
    StrategyPlan,
    StrategyRef,
)

# --------------------------------------------------------------------------- #
# small helpers (no Protocol, deterministic validation)
# --------------------------------------------------------------------------- #


class StrategyConfigError(ValueError):
    pass


_RESERVED_KEYS: set[str] = {"instance_id", "precedence"}


def _unknown_keys(cfg: Mapping[str, Any], allowed: set[str], *, ctx: str) -> None:
    extra = set(cfg.keys()) - allowed
    if extra:
        raise StrategyConfigError(f"{ctx}: unknown config keys: {sorted(extra)}")


def _opt_str(cfg: Mapping[str, Any], key: str) -> str | None:
    if key not in cfg:
        return None
    v = cfg[key]
    if not isinstance(v, str):
        raise StrategyConfigError(f"{key}: expected str, got {type(v).__name__}")
    return v


def _opt_int(cfg: Mapping[str, Any], key: str) -> int | None:
    if key not in cfg:
        return None
    v = cfg[key]
    if not isinstance(v, int):
        raise StrategyConfigError(f"{key}: expected int, got {type(v).__name__}")
    return v


def _opt_float(cfg: Mapping[str, Any], key: str) -> float | None:
    if key not in cfg:
        return None
    v = cfg[key]
    if isinstance(v, int):
        return float(v)
    if not isinstance(v, float):
        raise StrategyConfigError(f"{key}: expected float, got {type(v).__name__}")
    return v


def _plan_single(
    *,
    strategy_name: str,
    strategy_cls: type,
    config: Mapping[str, Any],
    ctor_kwargs: Mapping[str, Any],
    depends_on: tuple[str, ...] = (),
) -> list[StrategyPlan]:
    instance_id = str(config.get("instance_id") or "") or strategy_name
    precedence = int(config.get("precedence", getattr(strategy_cls, "precedence", 100)))

    # Always push precedence/instance_id into ctor kwargs so the instance matches the plan deterministically.
    full_kwargs = dict(ctor_kwargs)
    full_kwargs.setdefault("instance_id", instance_id)
    full_kwargs.setdefault("precedence", precedence)

    return [
        StrategyPlan(
            strategy_name=strategy_name,
            instance_id=instance_id,
            strategy_cls=strategy_cls,
            ctor_kwargs=full_kwargs,
            depends_on=depends_on,
            precedence=precedence,
        )
    ]


# --------------------------------------------------------------------------- #
# builtin config specs (these are what discover_config_specs loads)
# --------------------------------------------------------------------------- #


class Pep691IndexMetadataHttpStrategyConfig(BaseArtifactResolutionStrategyConfig[Any]):
    strategy_name: ClassVar[str] = Pep691IndexMetadataHttpStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        # Canonical defaults live here (not “magic” in strategy classes).
        return {
            "timeout_s": 30.0,
            "user_agent": "project-resolution-engine/0",
            "precedence": 50,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS | {"timeout_s", "user_agent"}
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        ctor: dict[str, Any] = {}
        if (v_timeout := _opt_float(config, "timeout_s")) is not None:
            ctor["timeout_s"] = v_timeout
        if (v_agent := _opt_str(config, "user_agent")) is not None:
            ctor["user_agent"] = v_agent

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs=ctor,
        )


class HttpWheelFileStrategyConfig(BaseArtifactResolutionStrategyConfig[Any]):
    strategy_name: ClassVar[str] = HttpWheelFileStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return {
            "timeout_s": 120.0,
            "user_agent": "project-resolution-engine/0",
            "chunk_bytes": 1024 * 1024,
            "precedence": 50,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS | {"timeout_s", "user_agent", "chunk_bytes"}
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        ctor: dict[str, Any] = {}
        if (v_timeout := _opt_float(config, "timeout_s")) is not None:
            ctor["timeout_s"] = v_timeout
        if (v_agent := _opt_str(config, "user_agent")) is not None:
            ctor["user_agent"] = v_agent
        if (v_chunk_bytes := _opt_int(config, "chunk_bytes")) is not None:
            ctor["chunk_bytes"] = v_chunk_bytes

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs=ctor,
        )


class Pep658CoreMetadataHttpStrategyConfig(BaseArtifactResolutionStrategyConfig[Any]):
    strategy_name: ClassVar[str] = Pep658CoreMetadataHttpStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return {
            "timeout_s": 30.0,
            "user_agent": "project-resolution-engine/0",
            "precedence": 50,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS | {"timeout_s", "user_agent"}
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        ctor: dict[str, Any] = {}
        if (v_timeout := _opt_float(config, "timeout_s")) is not None:
            ctor["timeout_s"] = v_timeout
        if (v_agent := _opt_str(config, "user_agent")) is not None:
            ctor["user_agent"] = v_agent

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs=ctor,
        )


class WheelExtractedCoreMetadataStrategyConfig(
    BaseArtifactResolutionStrategyConfig[Any]
):
    strategy_name: ClassVar[str] = WheelExtractedCoreMetadataStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        # The key point: this strategy must be configured with a wheel strategy to delegate to.
        return {
            "wheel_strategy_id": "wheel_http",
            "wheel_timeout_s": 120.0,
            "precedence": 90,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS | {"wheel_strategy_id", "wheel_timeout_s"}
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        wheel_sid = _opt_str(config, "wheel_strategy_id") or "wheel_http"

        # Injection is via StrategyRef, not by directly fetching instances here.
        wheel_ref: StrategyRef = StrategyRef(strategy_name=wheel_sid, instance_id=wheel_sid)

        ctor: dict[str, Any] = {
            "wheel_strategy": wheel_ref,
        }
        if (v := _opt_float(config, "wheel_timeout_s")) is not None:
            ctor["wheel_timeout_s"] = v

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs=ctor,
            depends_on=(wheel_ref.normalized_instance_id(),),
        )


class DirectUriWheelFileStrategyConfig(BaseArtifactResolutionStrategyConfig[Any]):
    strategy_name: ClassVar[str] = DirectUriWheelFileStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return {
            "chunk_bytes": 1024 * 1024,
            "precedence": 40,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS | {"chunk_bytes"}
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        ctor: dict[str, Any] = {}
        if (v := _opt_int(config, "chunk_bytes")) is not None:
            ctor["chunk_bytes"] = v

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs=ctor,
        )


class DirectUriCoreMetadataStrategyConfig(BaseArtifactResolutionStrategyConfig[Any]):
    """
    DirectUriCoreMetadataStrategyConfig is a configuration class for managing the artifact
    resolution strategy using direct URI core metadata.

    This class facilitates defining defaults and planning for the given strategy. It specifies
    the metadata and configuration required for implementing the artifact resolution logic.
    The class serves as a utility to handle initialization and validation of these settings to
    ensure compatibility within the artifact resolution framework.

    Attributes:
        strategy_name (ClassVar[str]): The name of the strategy leveraged by the class.
    """

    strategy_name: ClassVar[str] = DirectUriCoreMetadataStrategy.name

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return {
            "precedence": 40,
        }

    @classmethod
    def plan(
        cls, *, strategy_cls: type, config: Mapping[str, Any]
    ) -> list[StrategyPlan]:
        allowed = _RESERVED_KEYS
        _unknown_keys(config, allowed, ctx=cls.strategy_name)

        return _plan_single(
            strategy_name=cls.strategy_name,
            strategy_cls=strategy_cls,
            config=config,
            ctor_kwargs={},
        )
