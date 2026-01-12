from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from email.parser import Parser
from typing import Any, Iterable, Mapping, Sequence, cast, TypedDict, Literal, TypeVar, Generic, ClassVar

import pytest
from packaging.markers import Marker, Environment, default_environment
from packaging.specifiers import SpecifierSet

from project_resolution_engine.model.keys import ArtifactKind
from project_resolution_engine.model.resolution import (
    ResolutionMode,
    RequiresDistUrlPolicy,
    YankedWheelPolicy,
    PreReleasePolicy,
    InvalidRequiresDistPolicy
)
from project_resolution_engine.repository import ArtifactSource, ArtifactRepository
from project_resolution_engine.strategies import StrategyCriticality, IndexMetadataStrategy, CoreMetadataStrategy, \
    WheelFileStrategy, InstantiationPolicy, BaseArtifactResolutionStrategy
from unit.helpers.helper_validation import MirrorValidatableFake


def _reqtxt_meta(*, key: str | None = None, fmt: str | None = None) -> dict[str, Any]:
    """
    Mirrors the metadata shape used by the real reqtxt() helper:
      - "reqtxt": True
      - optional "reqtxt_key"
      - optional "reqtxt_fmt"
    """
    d: dict[str, Any] = {"reqtxt": True}
    if key is not None:
        d["reqtxt_key"] = key
    if fmt is not None:
        d["reqtxt_fmt"] = fmt
    return d


def _is_empty_collection(val: Any) -> bool:
    return isinstance(val, (set, frozenset, list, tuple, dict)) and len(val) == 0


_REQ_TXT_FMT: dict[str, Callable[[Iterable[str]], str]] = {"csv": lambda v: ",".join(sorted(v))}


def _reqtxt_comment_lines(obj: Any) -> list[str]:
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


def _coerce_field(value: Any) -> bool | Mapping[str, str]:
    # If it's a dict, keep it as-is
    if isinstance(value, Mapping):
        return dict(value)
    # Spec says it can be a boolean; anything else → False
    if isinstance(value, bool):
        return value
    return False


def validate_typed_dict(
        desc: str,
        mapping: Mapping[str, Any],
        validation_type: type,
        value_type: type | tuple[type, ...]) -> None:
    allowed_env_keys = set(validation_type.__annotations__.keys())
    bad_keys = set(mapping.keys()) - allowed_env_keys
    if bad_keys:
        raise ValueError(f"Invalid {desc} keys: {bad_keys}")
    bad_vals = [(k, type(v).__name__) for k, v in mapping.items() if not isinstance(v, value_type)]
    if bad_vals:
        details = ", ".join(f"{k} (got {t})" for k, t in bad_vals)
        expected = (
            value_type.__name__
            if isinstance(value_type, type)
            else " | ".join(t.__name__ for t in value_type))
        raise ValueError(f"Invalid {desc} values: expected {expected}; {details}")


# =============================================================================
# FAKES
# =============================================================================


@dataclass(frozen=True, slots=True)
class FakeBaseArtifactKey(MirrorValidatableFake, ABC):
    kind: ArtifactKind

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any],
                     **_: Any) -> FakeWheelKey | FakeIndexMetadataKey | FakeCoreMetadataKey:
        kind_mapping = mapping.get("kind", "none")
        kind = ArtifactKind(kind_mapping)
        match kind:
            case ArtifactKind.INDEX_METADATA:
                return FakeIndexMetadataKey.from_mapping(mapping)
            case ArtifactKind.CORE_METADATA:
                return FakeCoreMetadataKey.from_mapping(mapping)
            case ArtifactKind.WHEEL:
                return FakeWheelKey.from_mapping(mapping)
            case _:
                raise ValueError(f"Unknown artifact key kind: {kind_mapping!r}")


@dataclass(frozen=True, slots=True)
class FakeWheelKey(FakeBaseArtifactKey, MirrorValidatableFake):
    # ---- dataclass fields (match real names) ----
    name: str = field(metadata=_reqtxt_meta())
    version: str = field(metadata=_reqtxt_meta())
    tag: str = field(metadata=_reqtxt_meta())
    requires_python: str | None = field(default=None, compare=False, metadata=_reqtxt_meta())
    satisfied_tags: frozenset[str] = field(default_factory=frozenset, compare=False, metadata=_reqtxt_meta(fmt="csv"))
    dependency_ids: frozenset[str] | None = field(default=None, compare=False,
                                                  metadata=_reqtxt_meta(key="dependencies", fmt="csv"))
    origin_uri: str | None = field(default=None, compare=False, metadata=_reqtxt_meta())
    content_hash: str | None = field(default=None, compare=False)
    hash_algorithm: str | None = field(default=None, compare=False)
    marker: str | None = field(default=None, compare=False, metadata=_reqtxt_meta())
    extras: frozenset[str] | None = field(default=None, compare=False, metadata=_reqtxt_meta(fmt="csv"))
    kind: ArtifactKind = field(default=ArtifactKind.WHEEL, init=False, compare=False)
    _hash_spec: str | None = field(default=None, init=False, repr=False, compare=False,
                                   metadata=_reqtxt_meta(key="hash"))

    # ---- mirroring configuration ----
    # If you truly mirror everything, this can stay empty.
    MIRROR_IGNORE = frozenset()  # or {"kind"} if your real kind is an enum and you don't want to mirror its type
    MIRROR_INCLUDE_PRIVATE = True  # ensures _hash_spec is included in the check

    # ---- behavior ----

    @property
    def identifier(self) -> str:
        return "-".join((self.name.replace("-", "_"), self.version, self.tag))

    def as_tuple(self) -> tuple[str, str, str]:
        return self.name, self.version, self.tag

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, FakeWheelKey):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def set_origin_uri(self, origin_uri: str) -> None:
        if self.origin_uri is not None:
            raise ValueError("origin_uri is already set")
        object.__setattr__(self, "origin_uri", origin_uri)

    def set_content_hash(self, *, hash_algorithm: str, content_hash: str) -> None:
        if self.content_hash is not None or self.hash_algorithm is not None:
            raise ValueError("content hash is already set")
        object.__setattr__(self, "hash_algorithm", hash_algorithm)
        object.__setattr__(self, "content_hash", content_hash)
        object.__setattr__(self, "_hash_spec", f"{hash_algorithm.strip().lower()}:{content_hash.strip()}")

    @property
    def requirement_str(self) -> str:
        if self.origin_uri is None:
            raise ValueError(f"{self.identifier}: origin_uri is required to render a requirement string")
        if self._hash_spec is None:
            raise ValueError(f"{self.identifier}: _hash_spec is required to render a requirement string")
        return f"{self.name} @ {self.origin_uri} --hash={self._hash_spec}"

    @property
    def requirement_str_basic(self) -> str:
        return f"{self.name}=={self.version}"

    @property
    def req_txt_block(self) -> str:
        if self.origin_uri is None:
            raise ValueError(f"{self.identifier}: origin_uri is required to render requirements")
        if self._hash_spec is None:
            raise ValueError(f"{self.identifier}: _hash_spec is required to render requirements")
        meta_lines = _reqtxt_comment_lines(self)
        return "\n".join([*meta_lines, self.requirement_str])

    def to_mapping(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "version": self.version,
            "tag": self.tag,
            "requires_python": self.requires_python,
            "satisfied_tags": list(self.satisfied_tags),
            "dependencies": list(self.dependency_ids) if self.dependency_ids is not None else None,
            "origin_uri": self.origin_uri,
            "content_hash": self.content_hash,
            "hash_algorithm": self.hash_algorithm,
            "marker": self.marker,
            "extras": list(self.extras) if self.extras is not None else None,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeWheelKey:
        deps = mapping.get("dependencies")
        extras = mapping.get("extras")
        return cls(
            name=mapping["name"],
            version=mapping["version"],
            tag=mapping["tag"],
            requires_python=mapping.get("requires_python"),
            satisfied_tags=frozenset(mapping.get("satisfied_tags") or []),
            dependency_ids=frozenset(deps) if deps is not None else None,
            origin_uri=mapping.get("origin_uri"),
            content_hash=mapping.get("content_hash"),
            hash_algorithm=mapping.get("hash_algorithm"),
            marker=mapping.get("marker"),
            extras=frozenset(extras) if extras is not None else None)


@dataclass(kw_only=True, frozen=True, slots=True)
class FakeWheelSpec(MirrorValidatableFake):
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

    def to_mapping(self, *_: Any, **__: Any) -> Mapping[str, Any]:
        return {
            "name": self.name,
            "version": str(self.version) if self.version is not None else None,
            "extras": list(self.extras),
            "marker": str(self.marker) if self.marker is not None else None,
            "uri": self.uri,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], *_: Any, **__: Any) -> FakeWheelSpec:
        return cls(
            name=mapping["name"],
            version=SpecifierSet(mapping["version"]) if mapping["version"] is not None else None,
            extras=frozenset(mapping["extras"]),
            marker=Marker(mapping["marker"]) if mapping["marker"] is not None else None,
            uri=mapping["uri"])


@dataclass(frozen=True, slots=True)
class FakeIndexMetadataKey(FakeBaseArtifactKey, MirrorValidatableFake):
    project: str
    index_base: str = field(default="https://pypi.org/simple")
    kind: ArtifactKind = field(default=ArtifactKind.INDEX_METADATA, init=False)

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "index_base": self.index_base,
            "project": self.project
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeIndexMetadataKey:
        return cls(
            index_base=mapping["index_base"],
            project=mapping["project"])


@dataclass(frozen=True, slots=True)
class FakeCoreMetadataKey(FakeBaseArtifactKey, MirrorValidatableFake):
    name: str
    version: str
    tag: str
    file_url: str
    kind: ArtifactKind = field(default=ArtifactKind.CORE_METADATA, init=False)

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "version": self.version,
            "tag": self.tag,
            "file_url": self.file_url,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeCoreMetadataKey:
        return cls(
            name=mapping["name"],
            version=mapping["version"],
            tag=mapping["tag"],
            file_url=mapping["file_url"])


@dataclass(slots=True, frozen=True)
class FakeResolvedNode(MirrorValidatableFake):
    wheel_key: FakeWheelKey

    @property
    def name(self) -> str:
        return self.wheel_key.name

    @property
    def version(self) -> str:
        return self.wheel_key.version

    @property
    def tag(self) -> str:
        return self.wheel_key.tag

    @property
    def requires_python(self) -> str | None:
        return self.wheel_key.requires_python

    @property
    def satisfied_tags(self) -> frozenset[str]:
        return self.wheel_key.satisfied_tags

    @property
    def dependency_ids(self) -> frozenset[str] | None:
        return self.wheel_key.dependency_ids

    @property
    def origin_uri(self) -> str | None:
        return self.wheel_key.origin_uri

    @property
    def marker(self) -> str | None:
        return self.wheel_key.marker

    @property
    def extras(self) -> frozenset[str] | None:
        return self.wheel_key.extras

    @property
    def key(self) -> FakeWheelKey:
        return self.wheel_key

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "wheel_key": self.wheel_key.to_mapping()
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeResolvedNode:
        return cls(
            wheel_key=FakeWheelKey.from_mapping(mapping["wheel_key"]))


@dataclass(slots=True)
class FakeResolvedGraph(MirrorValidatableFake):
    supported_python_band: SpecifierSet
    _roots: set[FakeWheelKey]
    nodes: dict[FakeWheelKey, FakeResolvedNode]

    def __post_init__(self) -> None:
        node_keys = set(node_key.identifier for node_key in self.nodes.keys())
        root_keys = set(root_key.identifier for root_key in self._roots)

        # All roots must exist
        missing_roots = root_keys - node_keys
        if missing_roots:
            raise ValueError(f"Root nodes without metadata: {missing_roots}")

        # All dependencies must exist
        missing_deps: set[str] = set()
        for node in self.nodes.values():
            for dep_id in node.dependency_ids or ():
                if dep_id not in node_keys:
                    missing_deps.add(dep_id)

        if missing_deps:
            raise ValueError(f"Dependencies refer to missing nodes: {missing_deps}")

    @property
    def roots(self) -> list[FakeWheelKey]:
        return sorted(list(self._roots))

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "supported_python_band": str(self.supported_python_band),
            "roots": [r.to_mapping() for r in self.roots],
            "nodes": {
                wk.identifier: node.to_mapping() for wk, node in self.nodes.items()
            },
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeResolvedGraph:
        supported_python_band = SpecifierSet(mapping["supported_python_band"])
        root_items = mapping.get("roots") or []
        roots: set[FakeWheelKey] = {FakeWheelKey.from_mapping(r) for r in root_items}
        raw_nodes = mapping.get("nodes") or {}
        nodes: dict[FakeWheelKey, FakeResolvedNode] = {}
        for _, node_mapping in raw_nodes.items():
            node = FakeResolvedNode.from_mapping(node_mapping)
            nodes[node.key] = node
        return cls(supported_python_band=supported_python_band, _roots=roots, nodes=nodes)


@dataclass(slots=True, frozen=True)
class FakePep658Metadata(MirrorValidatableFake):
    name: str
    version: str
    requires_python: str | None
    requires_dist: frozenset[str]

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "requires_python": self.requires_python,
            "requires_dist": list(self.requires_dist),
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakePep658Metadata:
        return cls(
            name=str(mapping["name"]),
            version=str(mapping["version"]),
            requires_python=(mapping.get("requires_python") or None),
            requires_dist=frozenset(mapping.get("requires_dist") or []))

    @classmethod
    def from_core_metadata_text(cls, text: str) -> FakePep658Metadata:
        msg = Parser().parsestr(text)

        name = (msg.get("Name") or "").strip()
        version = (msg.get("Version") or "").strip()
        rp_raw = msg.get("Requires-Python")
        requires_python = rp_raw.strip() if rp_raw else None
        rd_headers = msg.get_all("Requires-Dist") or []
        requires_dist = [h.strip() for h in rd_headers if h.strip()]

        return cls.from_mapping({
            "name": name,
            "version": version,
            "requires_python": requires_python,
            "requires_dist": requires_dist,
        })


@dataclass(slots=True, frozen=True)
class FakePep691FileMetadata(MirrorValidatableFake):
    filename: str
    url: str
    hashes: Mapping[str, str]
    requires_python: str | None
    yanked: bool
    core_metadata: bool | Mapping[str, str]
    data_dist_info_metadata: bool | Mapping[str, str]

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "url": self.url,
            "hashes": dict(self.hashes),
            "requires_python": self.requires_python,
            "yanked": self.yanked,
            "core-metadata": self.core_metadata,
            "data-dist-info-metadata": self.data_dist_info_metadata,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakePep691FileMetadata:
        core_metadata: bool | Mapping[str, str] = _coerce_field(mapping.get("core-metadata"))
        data_dist_info_metadata: bool | Mapping[str, str] = _coerce_field(mapping.get("data-dist-info-metadata"))
        return cls(
            filename=mapping["filename"],
            url=mapping["url"],
            hashes=mapping["hashes"],
            requires_python=mapping.get("requires_python"),
            yanked=mapping["yanked"],
            core_metadata=core_metadata,
            data_dist_info_metadata=data_dist_info_metadata)


@dataclass(slots=True, frozen=True)
class FakePep691Metadata(MirrorValidatableFake):
    name: str
    files: Sequence[FakePep691FileMetadata]
    last_serial: int | None = None

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "name": self.name,
            "files": [f.to_mapping() for f in self.files],
            "last_serial": self.last_serial
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakePep691Metadata:
        files = [
            FakePep691FileMetadata.from_mapping(f)
            for f in mapping["files"]
            if isinstance(f, Mapping)
        ]
        last_serial = mapping.get("last_serial")
        return cls(
            name=mapping["name"],
            files=files,
            last_serial=int(last_serial) if last_serial is not None else None)


class FakeResolutionStrategyConfig(TypedDict, total=False):
    strategy_name: str
    instance_id: str
    precedence: int
    criticality: StrategyCriticality


@dataclass(kw_only=True, frozen=True, slots=True)
class FakeResolutionPolicy(MirrorValidatableFake):
    requires_dist_url_policy: RequiresDistUrlPolicy = RequiresDistUrlPolicy.IGNORE
    allowed_requires_dist_url_schemes: frozenset[str] | None = None
    yanked_wheel_policy: YankedWheelPolicy = YankedWheelPolicy.SKIP
    prerelease_policy: PreReleasePolicy = PreReleasePolicy.DEFAULT
    invalid_requires_dist_policy: InvalidRequiresDistPolicy = InvalidRequiresDistPolicy.SKIP

    def to_mapping(self, *args: Any, **kwargs: Any) -> Mapping[str, Any]:
        return {
            "requires_dist_url_policy": self.requires_dist_url_policy.value,
            "allowed_requires_dist_url_schemes": (
                sorted(self.allowed_requires_dist_url_schemes)
                if self.allowed_requires_dist_url_schemes is not None
                else None),
            "yanked_wheel_policy": self.yanked_wheel_policy.value,
            "prerelease_policy": self.prerelease_policy.value,
            "invalid_requires_dist_policy": self.invalid_requires_dist_policy.value,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], *args: Any, **kwargs: Any) -> FakeResolutionPolicy:
        schemes = mapping.get("allowed_requires_dist_url_schemes")
        allowed_schemes = None if schemes is None else frozenset(cast(str, s) for s in schemes)
        req_dist_url_policy = mapping.get("requires_dist_url_policy", RequiresDistUrlPolicy.IGNORE.value)
        yanked_wheel_policy = mapping.get("yanked_wheel_policy", YankedWheelPolicy.SKIP.value)
        prerelease_policy = mapping.get("prerelease_policy", PreReleasePolicy.DEFAULT.value)
        invalid_requires_dist_policy = mapping.get("invalid_requires_dist_policy", InvalidRequiresDistPolicy.SKIP.value)
        return cls(
            requires_dist_url_policy=RequiresDistUrlPolicy(req_dist_url_policy),
            allowed_requires_dist_url_schemes=allowed_schemes,
            yanked_wheel_policy=YankedWheelPolicy(yanked_wheel_policy),
            prerelease_policy=PreReleasePolicy(prerelease_policy),
            invalid_requires_dist_policy=InvalidRequiresDistPolicy(invalid_requires_dist_policy))


@dataclass(kw_only=True, frozen=True, slots=True)
class FakeResolutionEnv(MirrorValidatableFake):
    identifier: str
    supported_tags: frozenset[str]
    marker_environment: Environment = field(default_factory=default_environment)
    policy: FakeResolutionPolicy = field(default_factory=FakeResolutionPolicy)

    def to_mapping(self, *args, **kwargs) -> Mapping[str, Any]:
        return {
            "identifier": self.identifier,
            "supported_tags": list(self.supported_tags),
            "marker_environment": self.marker_environment,
            "policy": self.policy.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], *args, **kwargs) -> FakeResolutionEnv:
        env_map: dict[str, str] = mapping.get("marker_environment", {})
        validate_typed_dict("marker_environment", env_map, Environment, str)
        mrk_env = cast(Environment, cast(object, env_map))
        policy_map: dict[str, Any] = mapping.get("policy", FakeResolutionPolicy().to_mapping())
        return cls(
            identifier=mapping["identifier"],
            supported_tags=frozenset(mapping["supported_tags"]),
            marker_environment=mrk_env,
            policy=FakeResolutionPolicy.from_mapping(policy_map))


@dataclass(kw_only=True, frozen=True, slots=True)
class FakeResolutionParams(MirrorValidatableFake):
    root_wheels: list[FakeWheelSpec]
    target_environments: list[FakeResolutionEnv]
    resolution_mode: ResolutionMode = field(default=ResolutionMode.REQUIREMENTS_TXT)
    repo_id: str | None = None
    repo_config: Mapping[str, Any] | None = None
    strategy_configs: Iterable[FakeResolutionStrategyConfig] | None = field(default=None)


@dataclass(frozen=True, slots=True)
class FakeResolutionResult(MirrorValidatableFake):
    requirements_by_env: dict[str, str] = field(default_factory=dict)
    resolved_wheels_by_env: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeResolverRequirement(MirrorValidatableFake):
    wheel_spec: FakeWheelSpec

    @property
    def name(self) -> str:
        return self.wheel_spec.name.lower().replace("_", "-")

    @property
    def version(self) -> SpecifierSet | None:
        return self.wheel_spec.version

    @property
    def extras(self) -> frozenset[str]:
        return self.wheel_spec.extras

    @property
    def marker(self) -> Marker | None:
        return self.wheel_spec.marker

    @property
    def uri(self) -> str | None:
        return self.wheel_spec.uri

    def to_mapping(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {"wheel_spec": self.wheel_spec.to_mapping()}

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeResolverRequirement:
        return cls(wheel_spec=FakeWheelSpec.from_mapping(mapping["wheel_spec"]))


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeResolverCandidate(MirrorValidatableFake):
    wheel_key: FakeWheelKey

    @property
    def name(self) -> str:
        return self.wheel_key.name

    @property
    def version(self) -> str:
        return self.wheel_key.version

    @property
    def tag(self) -> str:
        return self.wheel_key.tag

    @property
    def requires_python(self) -> str | None:
        return self.wheel_key.requires_python

    @property
    def satisfied_tags(self) -> frozenset[str]:
        return self.wheel_key.satisfied_tags

    @property
    def dependency_ids(self) -> frozenset[str] | None:
        return self.wheel_key.dependency_ids

    @property
    def origin_uri(self) -> str | None:
        return self.wheel_key.origin_uri

    @property
    def marker(self) -> str | None:
        return self.wheel_key.marker

    @property
    def extras(self) -> frozenset[str] | None:
        return self.wheel_key.extras

    def to_mapping(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {"wheel_key": self.wheel_key.to_mapping()}

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeResolverCandidate:
        return cls(wheel_key=FakeWheelKey.from_mapping(mapping["wheel_key"]))


@dataclass(frozen=True, slots=True)
class FakeArtifactRecord(MirrorValidatableFake):
    key: FakeBaseArtifactKey
    destination_uri: str
    origin_uri: str
    source: ArtifactSource = ArtifactSource.OTHER
    content_sha256: str | None = None
    size: int | None = None
    created_at_epoch_s: float | None = None
    content_hashes: dict[str, str] = field(default_factory=dict)

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        mapping: dict[str, Any] = {
            "key": self.key.to_mapping(),
            "destination_uri": self.destination_uri,
            "origin_uri": self.origin_uri,
            "source": self.source.value,
            "content_sha256": self.content_sha256,
            "size": self.size,
            "created_at_epoch_s": self.created_at_epoch_s
        }
        if self.content_hashes:
            mapping.update({"content_hashes": self.content_hashes})
        return mapping

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> FakeArtifactRecord:
        incoming_hashes = mapping.get("content_hashes", {})
        return cls(
            key=FakeBaseArtifactKey.from_mapping(mapping["key"]),
            destination_uri=mapping["destination_uri"],
            origin_uri=mapping["origin_uri"],
            source=ArtifactSource(mapping.get("source", ArtifactSource.OTHER.value)),
            content_sha256=mapping.get("content_sha256"),
            size=mapping.get("size"),
            created_at_epoch_s=mapping.get("created_at_epoch_s"),
            content_hashes=dict(incoming_hashes))


ArtifactKeyType = TypeVar("ArtifactKeyType", bound=FakeBaseArtifactKey)


# ---------------------------------------------------------------------------
# Strategy fakes (MUST subclass the real base classes so isinstance(...) works)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConcreteFakeBaseArtifactResolutionStrategy(BaseArtifactResolutionStrategy):
    def resolve(self, *, key: Any, destination_uri: str) -> FakeArtifactRecord | None:
        return BaseArtifactResolutionStrategy.resolve(self, key=key, destination_uri=destination_uri)


@dataclass(frozen=True, slots=True)
class FakeIndexMetadataStrategy(IndexMetadataStrategy):
    def resolve(self, *, key: FakeIndexMetadataKey, destination_uri: str) -> FakeArtifactRecord | None:
        raise NotImplementedError("FakeIndexMetadataStrategy.resolve is not used by services.py tests")


@dataclass(frozen=True, slots=True)
class FakeCoreMetadataStrategy(CoreMetadataStrategy):
    def resolve(self, *, key: FakeCoreMetadataKey, destination_uri: str) -> FakeArtifactRecord | None:
        raise NotImplementedError("FakeCoreMetadataStrategy.resolve is not used by services.py tests")


@dataclass(frozen=True, slots=True)
class FakeWheelFileStrategy(WheelFileStrategy):
    def resolve(self, *, key: FakeWheelKey, destination_uri: str) -> FakeArtifactRecord | None:
        raise NotImplementedError("FakeWheelFileStrategy.resolve is not used by services.py tests")


# ---------------------------------------------------------------------------
# Capturing stub for services.load_strategies (patch services.load_strategies)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CapturingLoadStrategies:
    """
    Callable stub for services.load_strategies that records calls and returns a preset list.
    """
    return_value: Sequence[BaseArtifactResolutionStrategy[Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **kwargs: Any) -> list[BaseArtifactResolutionStrategy[Any]]:
        self.calls.append(dict(kwargs))
        return list(self.return_value)


# ---------------------------------------------------------------------------
# In-memory repository fake (generally useful; also good for coordinator tests)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InMemoryArtifactRepository(ArtifactRepository):
    """
    Minimal ArtifactRepository implementation backed by an in-memory dict.
    """
    records: dict[FakeBaseArtifactKey, FakeArtifactRecord] = field(default_factory=dict)

    get_calls: list[FakeBaseArtifactKey] = field(default_factory=list)
    put_calls: list[FakeArtifactRecord] = field(default_factory=list)
    delete_calls: list[FakeBaseArtifactKey] = field(default_factory=list)
    allocate_calls: list[FakeBaseArtifactKey] = field(default_factory=list)

    def get(self, key: FakeBaseArtifactKey) -> FakeArtifactRecord | None:
        self.get_calls.append(key)
        return self.records.get(key)

    def put(self, record: FakeArtifactRecord) -> None:
        self.put_calls.append(record)
        self.records[record.key] = record

    def delete(self, key: FakeBaseArtifactKey) -> None:
        self.delete_calls.append(key)
        self.records.pop(key, None)

    def allocate_destination_uri(self, key: FakeBaseArtifactKey) -> str:
        self.allocate_calls.append(key)
        payload = repr(key.to_mapping()).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()[:12]
        return f"mem://artifact/{key.kind.value}/{digest}"


# =============================================================================
# BUILDERS (fakes + mapping shapes that your real models expect)
# =============================================================================

def wk(
        name: str = "demo-pkg",
        version: str = "1.2.3",
        tag: str = "py3-none-any",
        *,
        deps: Sequence[FakeWheelKey] | None = None,
        dependency_ids: Iterable[str] | None = None,
        **kw: Any) -> FakeWheelKey:
    if deps is not None and dependency_ids is not None:
        raise ValueError("Specify only one of deps or dependency_ids")

    if deps is not None:
        dep_ids = frozenset(d.identifier for d in deps)
    elif dependency_ids is not None:
        dep_ids = frozenset(dependency_ids)
    else:
        dep_ids = None

    return FakeWheelKey(
        name=name,
        version=version,
        tag=tag,
        dependency_ids=dep_ids,
        **kw)


def wk_reqtxt(
        name: str = "demo-pkg",
        version: str = "1.2.3",
        tag: str = "py3-none-any",
        *,
        origin_uri: str = "https://example.invalid/demo-pkg-1.2.3-py3-none-any.whl",
        hash_algorithm: str = "sha256",
        content_hash: str = "0" * 64,
        **kw: Any) -> FakeWheelKey:
    k = wk(name=name, version=version, tag=tag, **kw)
    k.set_origin_uri(origin_uri)
    k.set_content_hash(hash_algorithm=hash_algorithm, content_hash=content_hash)
    return k


def ws(
        *,
        name: str = "demo-pkg",
        version: str | SpecifierSet | None = "==1.2.3",
        extras: Iterable[str] = (),
        marker: str | Marker | None = None,
        uri: str | None = None) -> FakeWheelSpec:
    v = version if isinstance(version, SpecifierSet) or version is None else SpecifierSet(version)
    m = marker if isinstance(marker, Marker) or marker is None else Marker(marker)
    return FakeWheelSpec(
        name=name,
        version=v,
        extras=frozenset(extras),
        marker=m,
        uri=uri)


def resolved_node_mapping(*, wheel_key: FakeWheelKey) -> dict[str, Any]:
    return {"wheel_key": wheel_key.to_mapping()}


def resolved_graph_mapping(
        *,
        supported_python_band: str = ">=3.10",
        roots: Sequence[FakeWheelKey],
        nodes: Sequence[FakeWheelKey]) -> dict[str, Any]:
    """
    Shape expected by ResolvedGraph.from_mapping:
      - supported_python_band: str
      - roots: list[wheel_key mapping]
      - nodes: {identifier: {"wheel_key": wheel_key mapping}}
    """
    return {
        "supported_python_band": supported_python_band,
        "roots": [r.to_mapping() for r in roots],
        "nodes": {n.identifier: resolved_node_mapping(wheel_key=n) for n in nodes},
    }


# noinspection PyTypeChecker
def make_fake_strategy(
        kind: Literal["index", "core", "wheel"],
        *,
        name: str,
        instance_id: str = "",
        precedence: int = 100,
        criticality: StrategyCriticality = StrategyCriticality.OPTIONAL,
        source: ArtifactSource = ArtifactSource.OTHER) -> BaseArtifactResolutionStrategy[Any]:
    """
    Factory for creating strategy instances for services.py tests.

    Note: instance_id defaults to the value of `name` if empty (via BaseArtifactResolutionStrategy.__post_init__).
    """
    match kind:
        case "index":
            return FakeIndexMetadataStrategy(
                name=name,
                instance_id=instance_id,
                precedence=precedence,
                criticality=criticality,
                source=source)
        case "core":
            return FakeCoreMetadataStrategy(
                name=name,
                instance_id=instance_id,
                precedence=precedence,
                criticality=criticality,
                source=source)
        case "wheel":
            return FakeWheelFileStrategy(
                name=name,
                instance_id=instance_id,
                precedence=precedence,
                criticality=criticality,
                source=source)
        case _:
            raise ValueError(f"Unknown kind: {kind!r}")


# =============================================================================
# PATCH UTILITIES (opt-in)
# =============================================================================

def patch_wheel_key_refs(monkeypatch: pytest.MonkeyPatch, *modules: Any) -> None:
    """
    Patch WheelKey *references* inside the given modules to FakeWheelKey.

    This is required when modules did:
      from ...keys import WheelKey
    because patching keys.WheelKey alone won’t update existing imports.
    """
    for m in modules:
        monkeypatch.setattr(m, "WheelKey", FakeWheelKey, raising=True)


def patch_wheel_spec_refs(monkeypatch: pytest.MonkeyPatch, *modules: Any) -> None:
    for m in modules:
        monkeypatch.setattr(m, "WheelSpec", FakeWheelSpec, raising=True)


@pytest.fixture
def patch_models_wheelkey(monkeypatch: pytest.MonkeyPatch) -> type[FakeWheelKey]:
    """
    Opt-in fixture: patch model modules so graph deserialization uses FakeWheelKey.
    """
    from project_resolution_engine.model import graph as model_graph
    patch_wheel_key_refs(monkeypatch, model_graph)
    return FakeWheelKey


@pytest.fixture
def patch_models_wheelspec(monkeypatch: pytest.MonkeyPatch) -> type[FakeWheelSpec]:
    """
    Opt-in fixture: patch model modules so resolution deserialization uses FakeWheelSpec.
    """
    from project_resolution_engine.model import resolution as model_resolution
    patch_wheel_spec_refs(monkeypatch, model_resolution)
    return FakeWheelSpec


def patch_services_load_strategies(
        monkeypatch: pytest.MonkeyPatch,
        *,
        return_value: Sequence[BaseArtifactResolutionStrategy[Any]]) -> CapturingLoadStrategies:
    """
    Patch the imported name inside services.py and return the capturing stub.
    """
    from project_resolution_engine import services as services_mod

    stub = CapturingLoadStrategies(return_value=return_value)
    monkeypatch.setattr(services_mod, "load_strategies", stub, raising=True)
    return stub
