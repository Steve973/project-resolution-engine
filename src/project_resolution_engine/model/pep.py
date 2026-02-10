from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from email.message import Message
from email.parser import Parser
from typing import Any

from typing_extensions import Self

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin


def _coerce_field(value: Any) -> bool | Mapping[str, str]:
    # If it's a dict, keep it as-is
    if isinstance(value, Mapping):
        return dict(value)
    # Spec says it can be a boolean; anything else → False
    if isinstance(value, bool):
        return value
    return False


@dataclass(slots=True, frozen=True)
class Pep658Metadata(MultiformatModelMixin):
    """
    Represents metadata conforming to the PEP 658 standard.

    Pep658Metadata encapsulates the details of a package's metadata as described
    by PEP 658. It provides mechanisms for constructing such metadata either from
    a mapping or from the core metadata text. This class is immutable and optimized
    for memory efficiency with `dataclass` slots enabled.

    Attributes:
        name (str): The name of the package.
        version (str): The version of the package.
        requires_python (str | None): The Python version requirement if specified,
            or None otherwise.
        requires_dist (frozenset[str]): A frozen set of dependencies required by
            the package.
    """

    name: str
    version: str
    requires_python: str | None
    requires_dist: frozenset[str]
    _parser: Parser = Parser()

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *_args, **_kwargs) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "requires_python": self.requires_python,
            "requires_dist": list(self.requires_dist),
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        """
        Create an instance of the class from a mapping object.

        This class method initializes a new object of the class by extracting
        values from the provided mapping object and converting them to the
        appropriate format for the class attributes.

        Args:
            mapping (Mapping[str, Any]): A dictionary-like object that should
                contain the necessary attributes such as 'name', 'version',
                'requires_python', and 'requires_dist' to create the instance.
            **_ (Any): Additional unused keyword arguments that are permitted
                but discarded during the instance creation process.

        Returns:
            Pep658Metadata: An instance of the class populated with the extracted
            and formatted values from the input mapping.
        """
        return cls(
            name=str(mapping["name"]),
            version=str(mapping["version"]),
            requires_python=(mapping.get("requires_python") or None),
            requires_dist=frozenset(mapping.get("requires_dist") or []),
        )

    @classmethod
    def from_core_metadata_text(cls, text: str) -> Pep658Metadata:
        """
        Creates an instance of Pep658Metadata from a PEP 658 core metadata text.

        The method parses the provided metadata text and extracts relevant information,
        such as the package name, version, Python version requirements, and distribution
        dependencies. The extracted information is then used to form a new instance
        of the Pep658Metadata class.

        Args:
            text (str): A string containing the PEP 658 core metadata.

        Returns:
            Pep658Metadata: An instance of the Pep658Metadata class populated with
            the parsed metadata.
        """
        msg: Message = cls._parser.parsestr(text)
        name: str = (msg.get("Name") or "").strip()
        version: str = (msg.get("Version") or "").strip()
        rp_raw: str = msg.get("Requires-Python")
        requires_python: str = rp_raw.strip() if rp_raw else None
        rd_headers: list[str] = msg.get_all("Requires-Dist") or []
        requires_dist: list[str] = [h.strip() for h in rd_headers if h.strip()]

        return cls.from_mapping(
            {
                "name": name,
                "version": version,
                "requires_python": requires_python,
                "requires_dist": requires_dist,
            }
        )


@dataclass(slots=True, frozen=True)
class Pep691FileMetadata(MultiformatModelMixin):
    filename: str
    url: str
    hashes: Mapping[str, str]
    requires_python: str | None
    yanked: bool
    core_metadata: bool | Mapping[str, str]
    data_dist_info_metadata: bool | Mapping[str, str]

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *_args, **_kwargs) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "url": self.url,
            "hashes": dict(self.hashes),
            "requires_python": self.requires_python,
            "yanked": self.yanked,
            "core-metadata": self.core_metadata,
            "data-dist-info-metadata": self.data_dist_info_metadata,
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        core_metadata: bool | Mapping[str, str] = _coerce_field(
            mapping.get("core-metadata")
        )
        data_dist_info_metadata: bool | Mapping[str, str] = _coerce_field(
            mapping.get("data-dist-info-metadata")
        )
        return cls(
            filename=mapping["filename"],
            url=mapping["url"],
            hashes=mapping["hashes"],
            requires_python=mapping.get("requires_python"),
            yanked=mapping["yanked"],
            core_metadata=core_metadata,
            data_dist_info_metadata=data_dist_info_metadata,
        )


@dataclass(slots=True, frozen=True)
class Pep691Metadata(MultiformatModelMixin):
    name: str
    files: Sequence[Pep691FileMetadata]
    last_serial: int | None = None

    # :: MechanicalOperation | type=serialization
    def to_mapping(self, *_args, **_kwargs) -> dict[str, Any]:
        return {
            "name": self.name,
            "files": [f.to_mapping() for f in self.files],
            "last_serial": self.last_serial,
        }

    # :: MechanicalOperation | type=deserialization
    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        files = [
            Pep691FileMetadata.from_mapping(f)
            for f in mapping["files"]
            if isinstance(f, Mapping)
        ]
        last_serial = mapping.get("last_serial")
        return cls(
            name=mapping["name"],
            files=files,
            last_serial=int(last_serial) if last_serial is not None else None,
        )
