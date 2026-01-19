from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Generic, TypedDict

from project_resolution_engine.model.keys import (
    IndexMetadataKey,
    CoreMetadataKey,
    WheelKey,
)
from project_resolution_engine.repository import (
    ArtifactKeyType,
    ArtifactRecord,
    ArtifactSource,
)


class InstantiationPolicy(str, Enum):
    """
    Controls whether a strategy type may have one instance or multiple instances.

    SINGLETON: exactly one instance is allowed (instance_id must equal strategy name).
    PROTOTYPE: one or more instances are allowed (instance_id values may differ).
    """

    SINGLETON = "singleton"
    PROTOTYPE = "prototype"


class StrategyCriticality(str, Enum):
    """
    Indicates whether a strategy should be considered and how strict the resolution chain is.

    IMPERATIVE: if any strategy is IMPERATIVE, only IMPERATIVE strategies are allowed to run.
    REQUIRED: strategy should be considered (if no IMPERATIVE strategies exist).
    OPTIONAL: strategy may be considered (if no IMPERATIVE strategies exist).
    DISABLED: strategy is not instantiated and not considered.
    """

    IMPERATIVE = "imperative"
    REQUIRED = "required"
    OPTIONAL = "optional"
    DISABLED = "disabled"


class ResolutionStrategyConfig(TypedDict, total=False):
    """
    Configuration dictionary for a specific strategy instance.

    The dict key in `strategy_configs_by_instance_id` is the canonical instance_id.

    Reserved keys:
      - strategy_name: binds this instance config to a strategy implementation type
      - instance_id: optional, but if present must match the dict key
      - precedence: per instance ordering precedence (lower runs earlier)
      - criticality: per instance criticality (including DISABLED)

    Any additional keys are passed through to the strategy constructor and/or consumed by
    the strategy config spec.
    """

    strategy_name: str
    instance_id: str
    precedence: int
    criticality: StrategyCriticality


class StrategyNotApplicable(Exception):
    """
    Used for normal control flow: "this strategy does not apply to this key".
    """

    pass


@dataclass(frozen=True, slots=True)
class BaseArtifactResolutionStrategy(Generic[ArtifactKeyType], ABC):
    """
    Base strategy contract (acquisition only).

    Important: a strategy must NOT consult or mutate repositories.
    It only resolves a key to a destination URI.

    instance_id defaults to `name` if empty.
    """

    name: str
    instance_id: str = ""
    precedence: int = 100
    criticality: StrategyCriticality = StrategyCriticality.OPTIONAL
    source: ArtifactSource = ArtifactSource.OTHER

    instantiation_policy: ClassVar[InstantiationPolicy] = InstantiationPolicy.SINGLETON

    def __post_init__(self) -> None:
        if not self.instance_id:
            object.__setattr__(self, "instance_id", self.name)

    @abstractmethod
    def resolve(
        self, *, key: ArtifactKeyType, destination_uri: str
    ) -> ArtifactRecord | None:
        """
        Attempt to resolve the key into a destination_uri.

        Return:
          - ArtifactRecord if resolved
          - None if not applicable (allowed but less explicit than raising)
        Raise:
          - StrategyNotApplicable for "not applicable" (preferred)
          - any other exception for real failures while attempting resolution
        """
        raise NotImplementedError


# -------------------------
# typed specializations
# -------------------------


@dataclass(frozen=True, slots=True)
class IndexMetadataStrategy(BaseArtifactResolutionStrategy[IndexMetadataKey], ABC):
    source: ArtifactSource = ArtifactSource.HTTP_PEP691


@dataclass(frozen=True, slots=True)
class CoreMetadataStrategy(BaseArtifactResolutionStrategy[CoreMetadataKey], ABC):
    source: ArtifactSource = ArtifactSource.HTTP_PEP658


@dataclass(frozen=True, slots=True)
class WheelFileStrategy(BaseArtifactResolutionStrategy[WheelKey], ABC):
    source: ArtifactSource = ArtifactSource.HTTP_WHEEL
