from __future__ import annotations

import re
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from enum import Enum
from functools import total_ordering
from typing import Mapping, Any, TypeVar, Iterable

from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from typing_extensions import Self

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SHA384_RE = re.compile(r"^[0-9a-fA-F]{96}$")
_SHA512_RE = re.compile(r"^[0-9a-fA-F]{128}$")
_REQ_TXT_FMT: dict[str, Callable[[Iterable[str]], str]] = {
    "csv": lambda v: ",".join(sorted(v))
}


class ArtifactKind(Enum):
    INDEX_METADATA = "index_metadata"
    CORE_METADATA = "core_metadata"
    WHEEL = "wheel"
    NONE = "none"


def _is_empty_collection(v: object) -> bool:
    return isinstance(v, (set, frozenset, list, tuple, dict)) and len(v) == 0


def normalize_project_name(project: str) -> str:
    """
    Normalize a project name for consistent keying.

    This uses packaging's canonicalize_name, which is what pip uses for normalization.
    """
    return canonicalize_name(project)


def reqtxt(*, key: str | None = None, fmt: str | None = None) -> dict[str, object]:
    md: dict[str, object] = {"reqtxt": True}
    if key is not None:
        md["reqtxt_key"] = key
    if fmt is not None:
        md["reqtxt_fmt"] = fmt
    return md


def _reqtxt_comment_lines(obj: WheelKey) -> list[str]:
    lines: list[str] = []
    for f in fields(obj):
        if not f.metadata.get("reqtxt"):
            continue

        val = getattr(obj, f.name)
        if val is None or _is_empty_collection(val):
            continue

        key = f.metadata.get("reqtxt_key", f.name)
        fmt_name = f.metadata.get("reqtxt_fmt")
        val_str = _REQ_TXT_FMT[str(fmt_name)](val) if fmt_name else str(val)

        lines.append(f"# {key}: {val_str}")

    return lines


@dataclass(frozen=True, slots=True)
class BaseArtifactKey(ABC, MultiformatModelMixin):
    kind: ArtifactKind

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> BaseArtifactKey:
        kind_mapping = mapping.get("kind", "none")
        kind = ArtifactKind(kind_mapping)
        match kind:
            case ArtifactKind.INDEX_METADATA:
                return IndexMetadataKey.from_mapping(mapping)
            case ArtifactKind.CORE_METADATA:
                return CoreMetadataKey.from_mapping(mapping)
            case ArtifactKind.WHEEL:
                return WheelKey.from_mapping(mapping)
            case _:
                raise ValueError(f"Unknown artifact key kind: {kind_mapping!r}")


ArtifactKeyType = TypeVar("ArtifactKeyType", bound=BaseArtifactKey)


@dataclass(frozen=True, slots=True)
class IndexMetadataKey(BaseArtifactKey):
    project: str
    index_base: str = field(default="https://pypi.org/simple")
    kind: ArtifactKind = field(default=ArtifactKind.INDEX_METADATA, init=False)

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "index_base": self.index_base,
            "project": self.project,
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        return cls(index_base=mapping["index_base"], project=mapping["project"])


@dataclass(frozen=True, slots=True)
class CoreMetadataKey(BaseArtifactKey):
    name: str
    version: str
    tag: str
    file_url: str
    kind: ArtifactKind = field(default=ArtifactKind.CORE_METADATA, init=False)

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "version": self.version,
            "tag": self.tag,
            "file_url": self.file_url,
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        return cls(
            name=mapping["name"],
            version=mapping["version"],
            tag=mapping["tag"],
            file_url=mapping["file_url"],
        )


@total_ordering
@dataclass(frozen=True, slots=True)
class WheelKey(BaseArtifactKey):
    """
    Represents a unique identification key for a Python wheel artifact.

    This class defines and manages the attributes necessary to uniquely identify
    and handle a Python wheel artifact. A wheel is a built package format for Python
    often used for distribution purposes. This class is immutable, has strict
    comparison capabilities, and provides a variety of methods for accessing and
    managing wheel metadata.

    Attributes:
        name (str): The normalized project name of the wheel.
        version (str): The version of the wheel, normalized if possible.
        tag (str): The compatibility tag associated with the wheel.
        requires_python (str | None): The optional Python requirement string for
            the wheel, specifying compatible Python versions.
        satisfied_tags (frozenset[str]): A set of tags denoting compatibility
            specifications for the wheel.
        dependency_ids (frozenset[str] | None): A set of IDs representing the
            dependencies of the wheel, if initialized.
        origin_uri (str | None): An optional URI that specifies the origin or
            source location of the wheel.
        content_hash (str | None): The optional hash of the wheel's content for
            integrity verification.
        hash_algorithm (str | None): The optional hashing algorithm used for the
            `content_hash`.
        marker (str | None): Optional environment markers for conditional
            dependencies.
        extras (frozenset[str] | None): Optional extra features provided by the
            wheel.
        kind (ArtifactKind): The artifact type, which is always set to `WHEEL` for
            this class.
    """

    name: str = field(metadata=reqtxt())
    version: str = field(metadata=reqtxt())
    tag: str = field(metadata=reqtxt())
    requires_python: str | None = field(default=None, compare=False, metadata=reqtxt())
    satisfied_tags: frozenset[str] = field(
        default_factory=frozenset, compare=False, metadata=reqtxt(fmt="csv")
    )
    dependency_ids: frozenset[str] | None = field(
        default=None, compare=False, metadata=reqtxt(key="dependencies", fmt="csv")
    )
    origin_uri: str | None = field(default=None, compare=False, metadata=reqtxt())
    content_hash: str | None = field(default=None, compare=False)
    hash_algorithm: str | None = field(default=None, compare=False)
    marker: str | None = field(default=None, compare=False, metadata=reqtxt())
    extras: frozenset[str] | None = field(
        default=None, compare=False, metadata=reqtxt(fmt="csv")
    )
    kind: ArtifactKind = field(default=ArtifactKind.WHEEL, init=False, compare=False)
    _hash_spec: str | None = field(
        default=None, init=False, repr=False, compare=False, metadata=reqtxt(key="hash")
    )

    def _validate_hash_and_set_spec(self) -> None:
        if self.hash_algorithm is None or self.content_hash is None:
            return
        alg = self.hash_algorithm.strip().lower()
        h = self.content_hash.strip()
        match alg:
            case "sha256":
                if not _SHA256_RE.match(h):
                    raise ValueError(f"Invalid SHA256 hash: {self.content_hash}")
            case "sha384":
                if not _SHA384_RE.match(h):
                    raise ValueError(f"Invalid SHA384 hash: {self.content_hash}")
            case "sha512":
                if not _SHA512_RE.match(h):
                    raise ValueError(f"Invalid SHA512 hash: {self.content_hash}")
            case _:
                pass  # tolerate unknown algorithms
        object.__setattr__(self, "_hash_spec", f"{alg}:{h}")

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", normalize_project_name(self.name))
        normalized_version: str = self.version
        try:
            normalized_version = str(Version(self.version))
        except InvalidVersion:
            pass
        object.__setattr__(self, "version", normalized_version)
        self._validate_hash_and_set_spec()

    # --------------------------------------------------------------------- #
    # One-time late property initialization
    # --------------------------------------------------------------------- #

    def set_dependency_ids(self, dependencies: Iterable[WheelKey]) -> None:
        if self.dependency_ids is not None:
            raise ValueError("WheelKey.dependency_ids is already set")
        object.__setattr__(
            self, "dependency_ids", frozenset(dep.identifier for dep in dependencies)
        )

    def set_origin_uri(self, origin_uri: str) -> None:
        if self.origin_uri is None:
            object.__setattr__(self, "origin_uri", origin_uri)
        else:
            raise ValueError("WheelKey.origin_uri is already set")

    def set_content_hash(self, *, hash_algorithm: str, content_hash: str) -> None:
        if self.content_hash is not None or self.hash_algorithm is not None:
            raise ValueError("WheelKey content hash is already set")
        object.__setattr__(self, "hash_algorithm", hash_algorithm)
        object.__setattr__(self, "content_hash", content_hash)
        self._validate_hash_and_set_spec()

    # --------------------------------------------------------------------- #
    # Convenience
    # --------------------------------------------------------------------- #

    def _proj_name_with_underscores(self) -> str:
        return self.name.replace("-", "_")

    @property
    def identifier(self) -> str:
        name = self._proj_name_with_underscores()
        version = self.version
        tag = self.tag
        return "-".join((name, version, tag))

    def as_tuple(self) -> tuple[str, str, str]:
        """
        Returns the identification-specific attributes of the WheelKey as a tuple.

        This method retrieves the `name`, `version`, and `tag` attributes of the object
        and returns them packed in a tuple. Thus, this serves as an "identity" tuple.

        Returns:
            tuple[str, str, str]: A tuple containing the `name`, `version`, and `tag`
            attributes of the object in the specified order.
        """
        return self.name, self.version, self.tag

    def __lt__(self, other: WheelKey) -> bool:
        return self.as_tuple() < other.as_tuple()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, WheelKey) and self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __str__(self) -> str:
        return self.identifier

    @property
    def requirement_str(self) -> str:
        if self.origin_uri is None:
            raise ValueError(
                f"{self.identifier}: origin_uri is required to render a requirement string"
            )
        if self._hash_spec is None:
            raise ValueError(
                f"{self.identifier}: _hash_spec is required to render a requirement string"
            )
        return f"{self.name} @ {self.origin_uri} --hash={self._hash_spec}"

    @property
    def requirement_str_basic(self) -> str:
        return f"{self.name}=={self.version}"

    @property
    def req_txt_block(self) -> str:
        """
        Returns the requirements text block for the associated package.

        This property generates a string representation of the package's requirements,
        including metadata and the formatted requirement line. It requires both the
        `origin_uri` and the private `_hash_spec` attributes to be set. If either
        is missing, a `ValueError` is raised.

        Raises:
            ValueError: If `origin_uri` is not set.
            ValueError: If `_hash_spec` is not set.

        Returns:
            str: A string containing the metadata comments (if any) and the formatted
            requirement line for the package.
        """
        if self.origin_uri is None:
            raise ValueError(
                f"{self.identifier}: origin_uri is required to render requirements"
            )
        if self._hash_spec is None:
            raise ValueError(
                f"{self.identifier}: _hash_spec is required to render requirements"
            )

        meta_lines = _reqtxt_comment_lines(self)
        req_line = self.requirement_str
        return "\n".join([*meta_lines, req_line])

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "version": self.version,
            "tag": self.tag,
            "requires_python": self.requires_python,
            "satisfied_tags": list(self.satisfied_tags),
            "dependencies": (
                list(self.dependency_ids) if self.dependency_ids is not None else None
            ),
            "origin_uri": self.origin_uri,
            "content_hash": self.content_hash,
            "hash_algorithm": self.hash_algorithm,
            "marker": self.marker,
            "extras": list(self.extras) if self.extras is not None else None,
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        dependencies_mapping = mapping.get("dependencies")
        extras_mapping = mapping.get("extras")
        return cls(
            name=mapping["name"],
            version=mapping["version"],
            tag=mapping["tag"],
            requires_python=mapping.get("requires_python"),
            satisfied_tags=frozenset(mapping.get("satisfied_tags", [])),
            dependency_ids=(
                frozenset(dependencies_mapping)
                if dependencies_mapping is not None
                else None
            ),
            origin_uri=mapping.get("origin_uri"),
            content_hash=mapping.get("content_hash"),
            hash_algorithm=mapping.get("hash_algorithm"),
            marker=mapping.get("marker"),
            extras=frozenset(extras_mapping) if extras_mapping is not None else None,
        )
