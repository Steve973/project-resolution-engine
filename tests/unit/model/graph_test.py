from __future__ import annotations

from typing import Any, Mapping

import pytest
from packaging.specifiers import SpecifierSet

from project_resolution_engine.model import graph as graph
from unit.helpers.models_helper import FakeWheelKey


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _wk(
        name: str,
        version: str,
        tag: str = "py3-none-any",
        *,
        dependency_ids: frozenset[str] | None = None) -> FakeWheelKey:
    return FakeWheelKey(name=name, version=version, tag=tag, dependency_ids=dependency_ids)


@pytest.fixture(autouse=True)
def _patch_wheelkey(monkeypatch: pytest.MonkeyPatch) -> None:
    # Strict unit boundary: Graph imports WheelKey, so patch at graph.WheelKey call-site.
    monkeypatch.setattr(graph, "WheelKey", FakeWheelKey)


# ------------------------------------------------------------------------------
# ResolvedNode
# ------------------------------------------------------------------------------

# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "prop, expected",
    [
        ("name", "demo-pkg"),
        ("version", "1.2.3"),
        ("tag", "py3-none-any"),
        ("requires_python", ">=3.9"),
        ("satisfied_tags", frozenset({"py3-none-any"})),
        ("dependency_ids", frozenset({"dep_1-0.1-py3-none-any"})),
        ("origin_uri", "https://example.invalid/demo.whl"),
        ("marker", "python_version >= '3.9'"),
        ("extras", frozenset({"fast"})),
    ],
)
def test_resolvednode_property_passthrough(prop: str, expected: Any) -> None:
    # Covers:
    # C001M001B0001..C001M009B0001 (property passthroughs)
    wk = FakeWheelKey(
        name="demo-pkg",
        version="1.2.3",
        tag="py3-none-any",
        requires_python=">=3.9",
        satisfied_tags=frozenset({"py3-none-any"}),
        dependency_ids=frozenset({"dep_1-0.1-py3-none-any"}),
        origin_uri="https://example.invalid/demo.whl",
        marker="python_version >= '3.9'",
        extras=frozenset({"fast"}))
    node = graph.ResolvedNode(wheel_key=wk)
    assert getattr(node, prop) == expected


# noinspection PyTypeChecker
def test_resolvednode_key_property() -> None:
    # Covers:
    # C001M010B0001
    wk = _wk("a", "1.0.0")
    node = graph.ResolvedNode(wheel_key=wk)
    assert node.key is wk


# noinspection PyTypeChecker
def test_resolvednode_to_mapping_delegates_to_wheelkey() -> None:
    # Covers:
    # C001M011B0001
    wk = _wk("a", "1.0.0")
    node = graph.ResolvedNode(wheel_key=wk)
    assert node.to_mapping() == {"wheel_key": wk.to_mapping()}


def test_resolvednode_from_mapping_uses_wheelkey_from_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    # Covers:
    # C001M012B0001
    sentinel = _wk("sentinel", "9.9.9")

    def _from_mapping(cls: type[FakeWheelKey], mapping: Mapping[str, Any], **_: Any) -> FakeWheelKey:
        assert mapping == {"name": "x", "version": "1", "tag": "t"}
        return sentinel

    monkeypatch.setattr(FakeWheelKey, "from_mapping", classmethod(_from_mapping))
    node = graph.ResolvedNode.from_mapping({"wheel_key": {"name": "x", "version": "1", "tag": "t"}})
    assert node.wheel_key is sentinel


# ------------------------------------------------------------------------------
# ResolvedGraph.__post_init__
# ------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_resolvedgraph_post_init_raises_for_missing_roots() -> None:
    # Covers:
    # C002M001B0001
    band = SpecifierSet(">=3.9")
    missing_root = _wk("root", "1.0.0")
    with pytest.raises(ValueError, match="Root nodes without metadata"):
        graph.ResolvedGraph(supported_python_band=band, _roots={missing_root}, nodes={})


def test_resolvedgraph_post_init_allows_empty_graph() -> None:
    # Covers:
    # C002M001B0002, C002M001B0003, C002M001B0010
    band = SpecifierSet(">=3.9")
    graph.ResolvedGraph(supported_python_band=band, _roots=set(), nodes={})


# noinspection PyTypeChecker
def test_resolvedgraph_post_init_node_loop_and_dep_loop_zero_ok() -> None:
    # Covers:
    # C002M001B0002, C002M001B0004, C002M001B0005, C002M001B0010
    band = SpecifierSet(">=3.9")
    wk = _wk("a", "1.0.0")
    node = graph.ResolvedNode(wheel_key=wk)
    graph.ResolvedGraph(supported_python_band=band, _roots={wk}, nodes={wk: node})


# noinspection PyTypeChecker
def test_resolvedgraph_post_init_raises_for_missing_dependency_id() -> None:
    # Covers:
    # C002M001B0002, C002M001B0004, C002M001B0006, C002M001B0007, C002M001B0009
    band = SpecifierSet(">=3.9")
    wk_a = _wk("a", "1.0.0")
    missing_dep_id = _wk("b", "2.0.0").identifier
    wk_a_with_dep = _wk("a", "1.0.0", dependency_ids=frozenset({missing_dep_id}))
    node_a = graph.ResolvedNode(wheel_key=wk_a_with_dep)
    with pytest.raises(ValueError, match="Dependencies refer to missing nodes"):
        graph.ResolvedGraph(supported_python_band=band, _roots={wk_a}, nodes={wk_a_with_dep: node_a})


# noinspection PyTypeChecker
def test_resolvedgraph_post_init_allows_when_dependency_present() -> None:
    # Covers:
    # C002M001B0002, C002M001B0004, C002M001B0006, C002M001B0008, C002M001B0010
    band = SpecifierSet(">=3.9")
    wk_a = _wk("a", "1.0.0")
    wk_b = _wk("b", "2.0.0")
    wk_a_with_dep = _wk("a", "1.0.0", dependency_ids=frozenset({wk_b.identifier}))
    node_a = graph.ResolvedNode(wheel_key=wk_a_with_dep)
    node_b = graph.ResolvedNode(wheel_key=wk_b)
    graph.ResolvedGraph(
        supported_python_band=band,
        _roots={wk_a},
        nodes={wk_a_with_dep: node_a, wk_b: node_b})


# ------------------------------------------------------------------------------
# ResolvedGraph.roots and to_mapping
# ------------------------------------------------------------------------------

# noinspection PyTypeChecker
def test_resolvedgraph_roots_sorted() -> None:
    # Covers:
    # C002M002B0001
    band = SpecifierSet(">=3.9")
    wk_b = _wk("b", "1.0.0")
    wk_a = _wk("a", "1.0.0")
    g = graph.ResolvedGraph(supported_python_band=band, _roots={wk_b, wk_a},
                            nodes={wk_a: graph.ResolvedNode(wk_a), wk_b: graph.ResolvedNode(wk_b)})
    assert g.roots == [wk_a, wk_b]


# noinspection PyTypeChecker
def test_resolvedgraph_to_mapping_structure() -> None:
    # Covers:
    # C002M003B0001
    band = SpecifierSet(">=3.9")
    wk_a = _wk("a", "1.0.0")
    wk_b = _wk("b", "2.0.0")
    node_a = graph.ResolvedNode(wheel_key=wk_a)
    node_b = graph.ResolvedNode(wheel_key=wk_b)

    g = graph.ResolvedGraph(supported_python_band=band, _roots={wk_b, wk_a}, nodes={wk_a: node_a, wk_b: node_b})
    m = g.to_mapping()

    assert m["supported_python_band"] == str(band)
    assert m["roots"] == [wk_a.to_mapping(), wk_b.to_mapping()]  # roots property sorts
    assert m["nodes"] == {
        wk_a.identifier: node_a.to_mapping(),
        wk_b.identifier: node_b.to_mapping(),
    }


# ------------------------------------------------------------------------------
# ResolvedGraph.from_mapping
# ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "roots_value, nodes_value, expected_root_count, expected_node_count, covers",
    [
        # mapping.get("roots") falsy -> []
        # mapping.get("nodes") falsy -> {}
        (None, None, 0, 0, {"C002M004B0002", "C002M004B0004", "C002M004B0005"}),
        # mapping.get("roots") truthy -> roots preserved
        # mapping.get("nodes") truthy -> nodes preserved, loop >= 1
        (
                [{"name": "a", "version": "1.0.0", "tag": "py3-none-any"}],
                {"ignored-key": {"wheel_key": {"name": "a", "version": "1.0.0", "tag": "py3-none-any"}}},
                1,
                1,
                {"C002M004B0001", "C002M004B0003", "C002M004B0006"},
        ),
    ],
)
def test_resolvedgraph_from_mapping_variants(
        roots_value: Any,
        nodes_value: Any,
        expected_root_count: int,
        expected_node_count: int,
        covers: set[str]) -> None:
    # Covers:
    # C002M004B0001..C002M004B0006 via parametrized variants
    payload: dict[str, Any] = {"supported_python_band": ">=3.9"}
    if roots_value is not None:
        payload["roots"] = roots_value
    if nodes_value is not None:
        payload["nodes"] = nodes_value

    g = graph.ResolvedGraph.from_mapping(payload)
    assert isinstance(g.supported_python_band, SpecifierSet)
    assert len(g.roots) == expected_root_count
    assert len(g.nodes) == expected_node_count

    # Sanity: if a node exists, it must be keyed by its node.key (WheelKey)
    for wk, node in g.nodes.items():
        assert node.key is wk
