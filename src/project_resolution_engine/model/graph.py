from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from packaging.specifiers import SpecifierSet
from typing_extensions import Self

from project_resolution_engine.internal.util.multiformat import MultiformatModelMixin
from project_resolution_engine.model.keys import WheelKey


@dataclass(slots=True, frozen=True)
class ResolvedNode(MultiformatModelMixin):
    """
    Represents a resolved node with metadata and dependencies that describe a
    Python package or distribution.

    A `ResolvedNode` encapsulates information about a package or distribution,
    such as its name, version, tag, required Python version, metadata, and its
    dependencies. The class can serialize itself into a dictionary representation
    and can be reconstructed from one. It is immutable and uses data slots for
    optimized memory usage.

    Attributes:
        wheel_key (WheelKey): Represents the unique identifier of the resolved
            node. It contains details like name, version, tag, required Python
            version, and other relevant metadata.
    """
    wheel_key: WheelKey

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
    def key(self) -> WheelKey:
        """
        Gets the `key` property, which represents the unique identifier of the wheel.

        Returns:
            WheelKey: A unique key object comprising the `name` and `version` attributes
            that represents the wheel uniquely.
        """
        return self.wheel_key

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        """
        Converts the object into a dictionary representation and returns it.

        Args:
            *args: Additional positional arguments that can be passed but are not
                explicitly used in the method.
            **kwargs: Additional keyword arguments that can be passed but are not
                explicitly used in the method.

        Returns:
            dict[str, Any]: A dictionary representation of the object with the
            attribute `wheel_key` mapped using its `to_mapping` method.
        """
        return {
            "wheel_key": self.wheel_key.to_mapping()
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        """
        Creates an instance of the class from a mapping. This constructor method
        parses input data to initialize an object instance.

        Args:
            mapping (Mapping[str, Any]): A dictionary-like object containing keys
                and values necessary to construct the object instance. The key
                'wheel_key' must exist within the mapping to successfully create
                the instance.

            **_ (Any): Additional unused keyword arguments.

        Returns:
            Self: An instance of the class initialized using the provided mapping.
        """

        return cls(
            wheel_key=WheelKey.from_mapping(mapping["wheel_key"]))


@dataclass(slots=True)
class ResolvedGraph(MultiformatModelMixin):
    """
    Result of resolving a chub's dependency tree against a CompatibilitySpec.

    This class represents the result of resolving a dependency tree for a chub
    package against a provided compatibility specification. It includes the
    starting points of resolution (roots) and the resulting mapping of nodes.
    The nodes detail connections and dependencies within the tree. The purpose
    of this class is to validate whether all root nodes and dependency
    relationships are fully resolved as part of the initialization process.

    Attributes:
        supported_python_band (SpecifierSet): The Python version band supported by this graph.
        _roots (set[WheelKey]): The starting (name, version) nodes representing
            the chub's dependencies as requested by the user.
        nodes (dict[WheelKey, ResolvedNode]): A canonical mapping from
            (name, version) pairs to ResolvedWheelNodes representing resolved
            dependencies and their metadata.
    """
    supported_python_band: SpecifierSet
    _roots: set[WheelKey]
    nodes: dict[WheelKey, ResolvedNode]

    def __post_init__(self) -> None:
        """
        Validates the topology of nodes and dependencies after initialization.

        This method performs two key checks:
        1. Ensures that all root nodes specified in the `_roots` attribute exist within the `nodes` dictionary.
        2. Verifies that all dependencies mentioned in each node's `dependencies` list are present as keys
           in the `nodes` dictionary.

        Raises:
            ValueError: If any root nodes specified in `_roots` are missing from the keys of `nodes`.
            ValueError: If dependencies in any node's `dependencies` list reference missing keys within `nodes`.

        """
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
    def roots(self) -> list[WheelKey]:
        """
        Gets the roots of the wheel keys.

        The roots represent a sorted list extracted from the internal data structure,
        which contains the foundational wheel keys.

        Returns:
            list[WheelKey]: A sorted list of wheel keys that are considered roots.
        """
        return sorted(list(self._roots))

    def to_mapping(self, *args, **kwargs) -> dict[str, Any]:
        """
        Converts the internal representation of the instance into a mapping (dictionary-like
        structure) format.

        This method serializes the object's data into a structured mapping suitable for
        further processing, such as serialization to JSON or other formats.

        Returns:
            Mapping[str, Any]: A dictionary-like structure containing the serialized data of the
            object. It includes the supported Python band, a list of roots with their names
            and versions, and a mapping of nodes with their identifier to their respective
            serialized mappings.
        """
        return {
            "supported_python_band": str(self.supported_python_band),
            "roots": [r.to_mapping() for r in self.roots],
            "nodes": {
                wk.identifier: node.to_mapping() for wk, node in self.nodes.items()
            },
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], **_: Any) -> Self:
        """
        Creates an instance of `CompatibilityResolution` from a mapping data structure.

        This factory method initializes a `CompatibilityResolution` object using data
        provided in a mapping format. It extracts the supported Python version band,
        root elements, and dependency nodes from the mapping and uses them to construct
        the object.

        Args:
            mapping (Mapping[str, Any]): The input mapping containing necessary details
                such as supported Python band, root elements, and dependency nodes.
            **_ (Any): Additional keyword arguments, which are ignored in this method.

        Returns:
            ResolvedGraph: A newly created instance of `CompatibilityResolution`.
        """
        supported_python_band = SpecifierSet(mapping["supported_python_band"])
        root_items = mapping.get("roots") or []
        roots: set[WheelKey] = {WheelKey.from_mapping(r) for r in root_items}
        raw_nodes = mapping.get("nodes") or {}
        nodes: dict[WheelKey, ResolvedNode] = {}
        for _, node_mapping in raw_nodes.items():
            node = ResolvedNode.from_mapping(node_mapping)
            nodes[node.key] = node
        return cls(supported_python_band=supported_python_band, _roots=roots, nodes=nodes)
