from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict, cast

from packaging.markers import Environment

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin


def validate_typed_dict(
    desc: str,
    mapping: Mapping[str, Any],
    validation_type: type,
    value_type: type | tuple[type, ...],
) -> None:
    """
    Validates a mapping against a given TypedDict definition for its keys and values.

    This function ensures that the provided mapping conforms to the specified TypedDict
    keys and value types. It identifies and reports any invalid keys not present in the
    TypedDict and values that do not match the expected types.

    Args:
        desc: Description of the mapping being validated, used for error messages.
        mapping: Mapping to be validated against the TypedDict definition.
        validation_type: TypedDict class to validate the keys of the mapping against.
        value_type: Expected type or tuple of types for the values in the mapping.

    Raises:
        ValueError: If there are keys in the mapping that are not allowed by the TypedDict
            definition, or if the values in the mapping do not match the expected type(s).
    """
    allowed_env_keys = set(validation_type.__annotations__.keys())
    bad_keys = set(mapping.keys()) - allowed_env_keys
    if bad_keys:
        raise ValueError(f"Invalid {desc} keys: {bad_keys}")
    bad_vals = [
        (k, type(v).__name__)
        for k, v in mapping.items()
        if not isinstance(v, value_type)
    ]
    if bad_vals:
        details = ", ".join(f"{k} (got {t})" for k, t in bad_vals)
        expected = (
            value_type.__name__
            if isinstance(value_type, type)
            else " | ".join(t.__name__ for t in value_type)
        )
        raise ValueError(f"Invalid {desc} values: expected {expected}; {details}")


class MarkerModeType(Enum):
    """
    Defines a set of enumeration values for marker mode types.

    This enumeration is used to represent the available modes for handling markers
    in a given context.

    Attributes:
        MERGE (str): Represents the "merge" mode. This mode handles markers
            by combining or merging relevant data or attributes.
        EXACT (str): Represents the "exact" mode. This mode requires an
            exact, precise handling or matching of markers.
    """

    MERGE = "merge"
    EXACT = "exact"


class EnvironmentOverrides(Environment, total=False):
    """
    Typed dictionary for overriding the Environment typed dictionary
    in packaging.markers.

    This class is used as a specialized mapping structure to provide
    optional overrides for environment attributes for the dependency
    tree that is being resolved.

    It extends the Environment structure with partial key coverage.
    """


@dataclass
class MarkerEnvConfig(MultiformatModelMixin):
    """
    Represents the configuration for a marker environment.

    This class is designed to manage settings through overrides and control the way
    those overrides are applied within the environment. The configuration can either
    merge a set of defaults with the provided overrides or use the overrides as the
    exact configuration.

    Attributes:
        overrides (MarkerEnvMap): A dictionary containing overrides for specific marker
            environment configurations.
        mode (str): Determines how the overrides are applied to the configuration.
            Acceptable values are:
                - "merge": Derive defaults, then override specific keys.
                - "exact": Use only the overrides as the configuration.
    """

    overrides: EnvironmentOverrides = field(
        default_factory=lambda: cast(EnvironmentOverrides, cast(object, {}))
    )
    mode: MarkerModeType = MarkerModeType.MERGE

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            "overrides": self.overrides,
            "mode": self.mode.value,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> MarkerEnvConfig:
        overrides = mapping.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError(
                f"Invalid overrides value: expected dict; got {type(overrides).__name__}"
            )
        overrides_map = overrides
        validate_typed_dict(
            "marker_env overrides", overrides_map, EnvironmentOverrides, str
        )
        env_overrides = cast(EnvironmentOverrides, cast(object, overrides_map))

        return cls(
            overrides=env_overrides,
            mode=MarkerModeType(mapping.get("mode", MarkerModeType.MERGE.value)),
        )


@dataclass
class Filter(MultiformatModelMixin):
    """
    Represents a unified include/exclude pattern.

    This class is used to define inclusion and exclusion patterns
    that can be applied to filter items based on specified criteria.
    It also includes an option to restrict filtering to the specified
    inclusion list.

    Attributes:
        include (list[str]): A list of patterns to include in the filter.
        exclude (list[str]): A list of patterns to exclude from the filter.
        specific_only (bool): If True, only use the include list and
            ignore generation.
    """

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    specific_only: bool = (
        False  # If true, ignore generation and only use the include list
    )

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            "include": self.include,
            "exclude": self.exclude,
            "specific_only": self.specific_only,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Filter:
        return cls(
            include=mapping.get("include", []),
            exclude=mapping.get("exclude", []),
            specific_only=mapping.get("specific_only", False),
        )


@dataclass
class VersionSpec(MultiformatModelMixin):
    """
    Version specification with range and filters.

    This class represents a version specification that includes a range and optional
    filters to further refine the specification. The `range` attribute defines a
    PEP 440 compliant version range (e.g., ">=3.10,<4.0"), or it can be `None` to
    indicate no specific range constraints. The `filters` attribute allows
    additional filtering criteria to be applied.

    Attributes:
        range (str | None): A PEP 440 compliant version range string or None to
            represent no range constraints.
        filters (Filter | None): Optional filters applied to further refine the
            version specification.
    """

    range: str | None = None  # PEP 440: ">=3.10,<4.0" or None for "all"
    filters: Filter | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {}
        if self.range is not None:
            result["range"] = self.range
        if self.filters is not None:
            result["filters"] = self.filters.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> VersionSpec:
        filters_data = mapping.get("filters")
        filters = Filter.from_mapping(filters_data) if filters_data else None

        return cls(range=mapping.get("range"), filters=filters)


@dataclass
class InterpreterConfig(MultiformatModelMixin):
    """
    Represents a Python interpreter configuration.

    This class is used to define the configuration for a Python interpreter, which includes the
    Python version, supported interpreter types, whether universal interpreters are accepted, and
    any additional filters that can be applied. It can also handle the conversion to and from a
    mapping representation, making it suitable for serialization and deserialization tasks.

    Attributes:
        python_version (VersionSpec): Specifies the Python version.
        types (list[str]): Defines the supported interpreter types (e.g., "py", "cp", "pp").
        accept_universal (bool): Indicates whether universal interpreters are accepted.
        filters (Filter | None): Specifies additional filters to apply, or None if no filters
            are defined.
    """

    python_version: VersionSpec
    types: list[str]
    accept_universal: bool = True
    filters: Filter | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {
            "python_version": self.python_version.to_mapping(),
            "types": self.types,
            "accept_universal": self.accept_universal,
        }
        if self.filters is not None:
            result["filters"] = self.filters.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> InterpreterConfig:
        filters_data = mapping.get("filters")
        filters = Filter.from_mapping(filters_data) if filters_data else None

        return cls(
            python_version=VersionSpec.from_mapping(mapping["python_version"]),
            types=mapping.get("types", ["cp"]),
            accept_universal=mapping.get("accept_universal", True),
            filters=filters,
        )


@dataclass
class AbiConfig(MultiformatModelMixin):
    """
    ABI configuration class, derived from `InterpreterConfig`.

    This class encapsulates configurations related to ABI (Application Binary
    Interface) and includes options for debugging, stability, and additional
    filters. It provides functionality for converting its contents to a mapping
    representation and creating an instance from such a mapping. This class is
    designed to be compatible with multiformat models via the `MultiformatModelMixin`.

    Attributes:
        include_debug (bool): Specifies whether debug builds should be included
            in the configuration. Defaults to False.
        include_stable (bool): Specifies whether stable builds (e.g., ABI3) should
            be included in the configuration. Defaults to True.
        filters (Filter | None): Optional filters to be applied as part of the
            configuration. The filters are represented by a `Filter` object or set
            to None if no filters are defined.
    """

    include_debug: bool = False
    include_stable: bool = True  # abi3
    filters: Filter | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {
            "include_debug": self.include_debug,
            "include_stable": self.include_stable,
        }
        if self.filters is not None:
            result["filters"] = self.filters.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> AbiConfig:
        filters_data = mapping.get("filters")
        filters = Filter.from_mapping(filters_data) if filters_data else None

        return cls(
            include_debug=mapping.get("include_debug", False),
            include_stable=mapping.get("include_stable", True),
            filters=filters,
        )


@dataclass
class PlatformVariant(MultiformatModelMixin):
    """
    Represents a platform variant such as manylinux or musllinux.

    This class is used to encapsulate information about a specific platform variant,
    which includes whether the platform is enabled and optionally its version
    specification. It is designed to support conversion between mapping structures
    and object representations.

    Attributes:
        enabled (bool): Indicates whether the platform variant is enabled.
        version (VersionSpec | None): The version specification of the platform
            variant, or None if no specific version is defined.
    """

    enabled: bool = True
    version: VersionSpec | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {
            "enabled": self.enabled,
        }
        if self.version is not None:
            result["version"] = self.version.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> PlatformVariant:
        version_data = mapping.get("version")
        version = VersionSpec.from_mapping(version_data) if version_data else None

        return cls(enabled=mapping.get("enabled", True), version=version)


@dataclass
class PlatformConfig(MultiformatModelMixin):
    """
    Represents platform-specific configuration details.

    This class is used to manage configuration options related to a specific platform,
    including supported architectures, platform variants, and filter criteria. It provides
    methods to convert the configuration to and from mappings, making it convenient for
    serialization and deserialization purposes.

    Attributes:
        enabled (bool): Indicates whether the platform configuration is enabled.
        arches (list[str]): A list of supported architectures for the platform.
        variants (dict[str, PlatformVariant]): A dictionary where keys represent the names
            of platform variants (e.g., "manylinux", "musllinux") and values are
            `PlatformVariant` instances.
        filters (Filter | None): An optional `Filter` object used to specify filtering
            criteria for the platform configuration.
    """

    enabled: bool = True
    arches: list[str] = field(default_factory=list)
    # Variants by name
    variants: dict[str, PlatformVariant] = field(
        default_factory=dict
    )  # "manylinux", "musllinux", etc.
    filters: Filter | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {
            "enabled": self.enabled,
            "arches": self.arches,
            "variants": {
                name: variant.to_mapping() for name, variant in self.variants.items()
            },
        }
        if self.filters is not None:
            result["filters"] = self.filters.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> PlatformConfig:
        filters_data = mapping.get("filters")
        filters = Filter.from_mapping(filters_data) if filters_data else None
        variants_data = mapping.get("variants", {})
        variants = {
            name: PlatformVariant.from_mapping(variant_data)
            for name, variant_data in variants_data.items()
        }

        return cls(
            enabled=mapping.get("enabled", True),
            arches=mapping.get("arches", []),
            variants=variants,
            filters=filters,
        )


@dataclass
class PlatformContext(MultiformatModelMixin):
    """
    Represents configuration for a specific platform or a universal context.

    This class serves to define the configuration details for a specific platform, interpreter,
    ABI, and compatibility tags which can be used for mapping and deriving platform-related
    data. It can convert the configuration to a dictionary-like mapping or build itself
    from a given mapping.

    Attributes:
        interpreter (InterpreterConfig | None): Configuration for the interpreter.
        abi (AbiConfig | None): Configuration for the application binary interface (ABI).
        platform (PlatformConfig | None): Configuration for the platform.
        compatibility_tags (Filter | None): Filter or complete override for compatibility tags.
        marker_env (MarkerEnvConfig | None): Configuration for marker environment handling.
    """

    interpreter: InterpreterConfig | None = None
    abi: AbiConfig | None = None
    platform: PlatformConfig | None = None
    # Optional: complete tag override
    compatibility_tags: Filter | None = None
    marker_env: MarkerEnvConfig | None = None

    def to_mapping(self) -> Mapping[str, Any]:
        result: dict[str, Any] = {}
        if self.interpreter is not None:
            result["interpreter"] = self.interpreter.to_mapping()
        if self.abi is not None:
            result["abi"] = self.abi.to_mapping()
        if self.platform is not None:
            result["platform"] = self.platform.to_mapping()
        if self.compatibility_tags is not None:
            result["compatibility_tags"] = self.compatibility_tags.to_mapping()
        if self.marker_env is not None:
            result["marker_env"] = self.marker_env.to_mapping()
        return result

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> PlatformContext:
        interpreter_data = mapping.get("interpreter")
        interpreter = (
            InterpreterConfig.from_mapping(interpreter_data)
            if interpreter_data
            else None
        )
        abi_data = mapping.get("abi")
        abi = AbiConfig.from_mapping(abi_data) if abi_data else None
        platform_data = mapping.get("platform")
        platform = PlatformConfig.from_mapping(platform_data) if platform_data else None
        tags_data = mapping.get("compatibility_tags")
        compatibility_tags = Filter.from_mapping(tags_data) if tags_data else None
        marker_env_data = mapping.get("marker_env")
        marker_env = (
            MarkerEnvConfig.from_mapping(marker_env_data) if marker_env_data else None
        )

        return cls(
            interpreter=interpreter,
            abi=abi,
            platform=platform,
            compatibility_tags=compatibility_tags,
            marker_env=marker_env,
        )


class PlatformOverrides(TypedDict, total=False):
    """
    Represents platform-specific overrides for a given context.

    This class is a typed dictionary used to define settings or configurations
    specific to various operating platforms. It allows providing optional
    platform-specific contexts for Android, iOS, Linux, macOS, and Windows.
    Each platform context can be set to either a `PlatformContext` object
    or None if no override is required for that platform.

    Attributes:
        android (PlatformContext | None): The context override for the Android platform.
            Set to None if there is no specific override for Android.
        ios (PlatformContext | None): The context override for the iOS platform.
            Set to None if there is no specific override for iOS.
        linux (PlatformContext | None): The context override for the Linux platform.
            Set to None if there is no specific override for Linux.
        macos (PlatformContext | None): The context override for the macOS platform.
            Set to None if there is no specific override for macOS.
        windows (PlatformContext | None): The context override for the Windows platform.
            Set to None if there is no specific override for Windows.
    """

    android: PlatformContext
    ios: PlatformContext
    linux: PlatformContext
    macos: PlatformContext
    windows: PlatformContext


@dataclass
class ResolutionContext(MultiformatModelMixin):
    """Represents a resolution context with universal defaults and platform-specific overrides.

    This class provides a structured way to define resolution contexts, including
    a universal configuration shared across platforms and platform-specific
    overrides for finer customization. It also allows serialization to and from
    mappings, making it suitable for handling data persistence or interchange.

    Attributes:
        name (str): The name of the resolution context.
        universal (PlatformContext): The universal/default platform configuration
            that applies across all platforms.
        platform_overrides (PlatformOverrides): A dictionary containing platform-specific
            overrides for the resolution context.
    """

    name: str
    universal: PlatformContext
    platform_overrides: PlatformOverrides = field(
        default_factory=lambda: cast(PlatformOverrides, cast(object, {}))
    )

    def to_mapping(self) -> Mapping[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "universal": self.universal.to_mapping(),
        }
        if self.platform_overrides:
            out.update(
                platform_overrides={
                    k: cast(PlatformContext, v).to_mapping()
                    for k, v in self.platform_overrides.items()
                }
            )
        return out

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> ResolutionContext:
        raw = mapping.get("platform_overrides", {})
        if not isinstance(raw, Mapping):
            raise ValueError("platform_overrides must be a mapping")

        parsed: dict[str, PlatformContext] = {}
        for platform_name, value in raw.items():
            if value is None:
                continue
            if not isinstance(value, Mapping):
                raise ValueError(
                    f"platform_overrides.{platform_name} must be a mapping"
                )
            parsed[platform_name] = PlatformContext.from_mapping(value)

        validate_typed_dict(
            "platform overrides", parsed, PlatformOverrides, PlatformContext
        )

        return cls(
            name=mapping["name"],
            universal=PlatformContext.from_mapping(mapping["universal"]),
            platform_overrides=cast(PlatformOverrides, cast(object, parsed)),
        )
