from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Any, Mapping, TYPE_CHECKING, TypeVar

from packaging.utils import canonicalize_name
from typing_extensions import Self

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin

if TYPE_CHECKING:
    from project_resolution_engine.model.keys import BaseArtifactKey

    ArtifactKeyType = TypeVar("ArtifactKeyType", bound="BaseArtifactKey")
else:
    ArtifactKeyType = TypeVar("ArtifactKeyType")

REPOSITORY_ENTRYPOINT_GROUP = "project_resolution_engine.repositories"


def reqtxt(*, key: str | None = None, fmt: str | None = None) -> dict[str, object]:
    md: dict[str, object] = {"reqtxt": True}
    if key is not None:
        md["reqtxt_key"] = key
    if fmt is not None:
        md["reqtxt_fmt"] = fmt
    return md


def _is_empty_collection(v: object) -> bool:
    return isinstance(v, (set, frozenset, list, tuple, dict)) and len(v) == 0


def normalize_project_name(project: str) -> str:
    """
    Normalize a project name for consistent keying.

    This uses packaging's canonicalize_name, which is what pip uses for normalization.
    """
    return canonicalize_name(project)


class ArtifactKind(Enum):
    INDEX_METADATA = "index_metadata"
    CORE_METADATA = "core_metadata"
    WHEEL = "wheel"
    NONE = "none"


class ArtifactSource(Enum):
    HTTP_PEP691 = "http_pep691"
    HTTP_PEP658 = "http_pep658"
    HTTP_WHEEL = "http_wheel"
    URI_WHEEL = "uri_wheel"
    WHEEL_EXTRACTED = "wheel_extracted"
    OTHER = "other"


class ArtifactRepository(ABC):
    @abstractmethod
    def get(self, key: BaseArtifactKey) -> ArtifactRecord | None: ...

    @abstractmethod
    def put(self, record: ArtifactRecord) -> None: ...

    @abstractmethod
    def delete(self, key: BaseArtifactKey) -> None: ...

    @abstractmethod
    def allocate_destination_uri(self, key: BaseArtifactKey) -> str: ...

    def close(self) -> None:
        """
        Cleanup hook for repositories.

        The default implementation is a no-op. Override in repositories
        that hold resources (file handles, connections, temp dirs, etc.).
        """
        return None


class ArtifactResolver(Generic[ArtifactKeyType], ABC):
    @abstractmethod
    def resolve(self, key: ArtifactKeyType, destination_uri: str) -> ArtifactRecord: ...


@dataclass(frozen=True, slots=True)
class ArtifactRecord(MultiformatModelMixin):
    key: BaseArtifactKey
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
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        incoming_hashes = mapping.get("content_hashes", {})
        return cls(
            key=BaseArtifactKey.from_mapping(mapping["key"]),
            destination_uri=mapping["destination_uri"],
            origin_uri=mapping["origin_uri"],
            source=ArtifactSource(mapping.get("source", ArtifactSource.OTHER.value)),
            content_sha256=mapping.get("content_sha256"),
            size=mapping.get("size"),
            created_at_epoch_s=mapping.get("created_at_epoch_s"),
            content_hashes=dict(incoming_hashes))
