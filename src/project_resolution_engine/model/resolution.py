from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast, Mapping, Sequence

from packaging.markers import Environment, default_environment, Marker
from packaging.specifiers import SpecifierSet
from typing_extensions import Self

from project_resolution_engine.internal.compatibility import validate_typed_dict
from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin
from project_resolution_engine.model.keys import BaseArtifactKey
from project_resolution_engine.strategies import ResolutionStrategyConfig


class ResolutionMode(Enum):
    REQUIREMENTS_TXT = "requirements_txt"
    RESOLVED_WHEELS = "resolved_wheels"


class RequiresDistUrlPolicy(Enum):
    HONOR = "honor"  # use req.url as WheelSpec.uri
    IGNORE = "ignore"  # drop req.url, resolve by name and specifier
    RAISE = "raise"  # fail fast


class YankedWheelPolicy(Enum):
    SKIP = "skip"  # current behavior
    ALLOW = "allow"  # allow yanked wheels to participate


class PreReleasePolicy(Enum):
    DEFAULT = "default"  # let packaging decide (SpecifierSet prerelease rules)
    ALLOW = "allow"  # treat prereleases as allowed for contains checks
    DISALLOW = "disallow"  # treat prereleases as not allowed for contains checks


class InvalidRequiresDistPolicy(Enum):
    SKIP = "skip"  # current behavior (continue)
    RAISE = "raise"  # fail fast


@dataclass(kw_only=True, frozen=True, slots=True)
class ResolutionPolicy(MultiformatModelMixin):
    """
    Policy knobs that influence resolution behavior but are not intrinsic properties of
    the target interpreter or platform.

    This class is designed to live on a ResolutionEnv, allowing users to customize
    resolution policies for specific target environments. It encapsulates various
    adjustable settings to control aspects of dependency resolution.

    Attributes:
        requires_dist_url_policy (RequiresDistUrlPolicy): Defines the policy governing
            how `requires_dist` URLs are handled during resolution.
        allowed_requires_dist_url_schemes (frozenset[str] | None): Specifies the
            allowed URL schemes for `requires_dist` dependencies. A value of None permits
            any scheme, delegating the decision on handling to strategies.
        yanked_wheel_policy (YankedWheelPolicy): Dictates the handling of yanked
            wheels during resolution.
        prerelease_policy (PreReleasePolicy): Defines the policy for handling
            prerelease versions of dependencies.
        invalid_requires_dist_policy (InvalidRequiresDistPolicy): Specifies the
            behavior when encountering invalid values in `requires_dist`.
    """

    requires_dist_url_policy: RequiresDistUrlPolicy = RequiresDistUrlPolicy.IGNORE
    allowed_requires_dist_url_schemes: frozenset[str] | None = None
    yanked_wheel_policy: YankedWheelPolicy = YankedWheelPolicy.SKIP
    prerelease_policy: PreReleasePolicy = PreReleasePolicy.DEFAULT
    invalid_requires_dist_policy: InvalidRequiresDistPolicy = (
        InvalidRequiresDistPolicy.SKIP
    )

    def to_mapping(self, *args: Any, **kwargs: Any) -> Mapping[str, Any]:
        return {
            "requires_dist_url_policy": self.requires_dist_url_policy.value,
            "allowed_requires_dist_url_schemes": (
                sorted(self.allowed_requires_dist_url_schemes)
                if self.allowed_requires_dist_url_schemes is not None
                else None
            ),
            "yanked_wheel_policy": self.yanked_wheel_policy.value,
            "prerelease_policy": self.prerelease_policy.value,
            "invalid_requires_dist_policy": self.invalid_requires_dist_policy.value,
        }

    @classmethod
    def from_mapping(
        cls, mapping: Mapping[str, Any], *args: Any, **kwargs: Any
    ) -> Self:
        schemes = mapping.get("allowed_requires_dist_url_schemes")
        allowed_schemes = (
            None if schemes is None else frozenset(cast(str, s) for s in schemes)
        )
        req_dist_url_policy = mapping.get(
            "requires_dist_url_policy", RequiresDistUrlPolicy.IGNORE.value
        )
        yanked_wheel_policy = mapping.get(
            "yanked_wheel_policy", YankedWheelPolicy.SKIP.value
        )
        prerelease_policy = mapping.get(
            "prerelease_policy", PreReleasePolicy.DEFAULT.value
        )
        invalid_requires_dist_policy = mapping.get(
            "invalid_requires_dist_policy", InvalidRequiresDistPolicy.SKIP.value
        )
        return cls(
            requires_dist_url_policy=RequiresDistUrlPolicy(req_dist_url_policy),
            allowed_requires_dist_url_schemes=allowed_schemes,
            yanked_wheel_policy=YankedWheelPolicy(yanked_wheel_policy),
            prerelease_policy=PreReleasePolicy(prerelease_policy),
            invalid_requires_dist_policy=InvalidRequiresDistPolicy(
                invalid_requires_dist_policy
            ),
        )


@dataclass(kw_only=True, frozen=True, slots=True)
class ResolutionEnv(MultiformatModelMixin):
    identifier: str
    supported_tags: frozenset[str]
    marker_environment: Environment = field(default_factory=default_environment)
    policy: ResolutionPolicy = field(default_factory=ResolutionPolicy)

    def to_mapping(self, *args, **kwargs) -> Mapping[str, Any]:
        return {
            "identifier": self.identifier,
            "supported_tags": list(self.supported_tags),
            "marker_environment": self.marker_environment,
            "policy": self.policy.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], *args, **kwargs) -> Self:
        env_map: dict[str, str] = mapping.get("marker_environment", {})
        validate_typed_dict("marker_environment", env_map, Environment, str)
        mrk_env = cast(Environment, cast(object, env_map))
        policy_map: dict[str, Any] = mapping.get(
            "policy", ResolutionPolicy().to_mapping()
        )
        return cls(
            identifier=mapping["identifier"],
            supported_tags=frozenset(mapping["supported_tags"]),
            marker_environment=mrk_env,
            policy=ResolutionPolicy.from_mapping(policy_map),
        )


@dataclass(kw_only=True, frozen=True, slots=True)
class WheelSpec(MultiformatModelMixin):
    """
    Represents a specification for a Python wheel, akin to pip's requirement specifier.

    The intent is for this to be familiar to pip users when they use a requirement
    specifier.

    This class models the characteristics of a wheel specification, supporting
    the inclusion of optional extras, environment markers, and URIs. If a URI
    is provided, it takes precedence over the version attribute, aligning with
    the versioning specified in the URI.

    Attributes:
        name (str): The name of the wheel, required for identification purposes.
        version (str): The version specifier for the wheel, unless overridden
            by a URI.
        extras (frozenset[str]): An optional set of additional features or
            components to be included.
        marker (str | None): An optional environment marker that defines the
            conditions under which the wheel is applicable.
        uri (str | None): An optional URI that, if present, specifies the
            requirement source and overrides the `version` attribute.
    """

    name: str
    version: SpecifierSet | None = field(default=None)
    extras: frozenset[str] = field(default_factory=frozenset)
    marker: Marker | None = field(default=None)
    uri: str | None = field(default=None)

    def __post_init__(self) -> None:
        u = (self.uri.strip() or None) if self.uri is not None else None
        object.__setattr__(self, "uri", u)
        if self.uri is None and self.version is None:
            raise ValueError("Must specify either a version or a URI")

    @property
    def identifier(self) -> str:
        return f"{self.name}-{self.version}"

    def __str__(self) -> str:
        return self.identifier

    def to_mapping(self, *args, **kwargs) -> Mapping[str, Any]:
        return {
            "name": self.name,
            "version": str(self.version) if self.version is not None else None,
            "extras": list(self.extras),
            "marker": str(self.marker) if self.marker is not None else None,
            "uri": self.uri,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], *args, **kwargs) -> Self:
        return cls(
            name=mapping["name"],
            version=(
                SpecifierSet(mapping["version"])
                if mapping["version"] is not None
                else None
            ),
            extras=frozenset(mapping["extras"]),
            marker=Marker(mapping["marker"]) if mapping["marker"] is not None else None,
            uri=mapping["uri"],
        )


@dataclass(kw_only=True, frozen=True, slots=True)
class ResolutionParams:
    """
    Representation of resolution parameters for a dependency resolution process.

    This class encapsulates the configuration and parameters necessary to resolve dependencies
    for a target environment using specific resolution strategies and modes. It includes support
    for specifying resolution behaviors, repository details, and ordering preferences. The class
    is immutable and designed to ensure well-structured inputs for resolution workflows.

    Attributes:
        root_wheels (list[WheelSpec]): The list of root wheel specifications to be resolved.
        target_environments (list[ResolutionEnv]): The list of target environments for which the
            resolution process should be performed.
        resolution_mode (ResolutionMode): The mode of resolution, defaulting to REQUIREMENTS_TXT.
        repo_id (str | None): Optional identifier for the repository from which to store/fetch artifacts.
        repo_config (Mapping[str, Any] | None): Optional configuration mapping for the repository.
        strategy_configs (Iterable[ResolutionStrategyConfig] | None): Optional set of per-instance
            configurations for resolution strategies.
    """

    root_wheels: list[WheelSpec]
    target_environments: list[ResolutionEnv]
    resolution_mode: ResolutionMode = field(default=ResolutionMode.REQUIREMENTS_TXT)
    repo_id: str | None = None
    repo_config: Mapping[str, Any] | None = None
    strategy_configs: Iterable[ResolutionStrategyConfig] | None = field(default=None)


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    requirements_by_env: dict[str, str] = field(default_factory=dict)
    resolved_wheels_by_env: dict[str, list[str]] = field(default_factory=dict)


class ResolutionError(Exception):
    """
    Base error type for resolution orchestration failures.
    """


class ArtifactResolutionError(ResolutionError):
    """
    Raised when an ArtifactResolver cannot resolve an artifact after trying all strategies.
    """

    def __init__(
        self,
        message: str,
        *,
        key: BaseArtifactKey,
        causes: Sequence[BaseException] = (),
    ):
        super().__init__(message)
        self.key = key
        self.causes = tuple(causes)
