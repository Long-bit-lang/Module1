# Có thể thêm test nếu cần
# Bảng benchmark ở docs/ALGORITHM_BENCHMARK.md
import pytest
import random

from core.road_graph import RoadGraph
from core.strategies import (
    STRATEGIES,
    DijkstraPerDriver,
    ReverseDijkstra,
)


def test_road_graph_node_and_edge_api(small_graph: RoadGraph) -> None:
    assert small_graph.has_node("N5")
    assert not small_graph.has_node("missing")
    assert small_graph.neighbors("missing") == []
    assert small_graph.edges() == [
        ("N1", "N2", 2.0),
        ("N1", "N3", 6.0),
        ("N2", "N3", 1.0),
        ("N2", "N4", 4.0),
        ("N3", "N4", 2.0),
    ]


def test_reverse_graph_keeps_isolated_nodes(small_graph: RoadGraph) -> None:
    reversed_graph = small_graph.reversed()

    assert reversed_graph.nodes() == small_graph.nodes()
    assert reversed_graph.has_node("N5")
    assert reversed_graph.neighbors("N4") == [("N2", 4.0), ("N3", 2.0)]


def test_road_graph_rejects_invalid_weights() -> None:
    graph = RoadGraph()
    for weight in (-1, float("inf"), float("nan"), True):
        with pytest.raises((TypeError, ValueError)):
            graph.add_edge("N1", "N2", weight)
    assert graph.nodes() == []


def test_a1_a2_match_optimal_driver_and_path(small_graph: RoadGraph) -> None:
    free_drivers = {"D1": "N1", "D2": "N2", "D3": "N5"}

    a1 = DijkstraPerDriver().find_driver(small_graph, "N4", free_drivers)
    a2 = ReverseDijkstra().find_driver(small_graph, "N4", free_drivers)

    assert (a1.driver_id, a1.eta, a1.path) == ("D2", 3.0, ["N2", "N3", "N4"])
    assert (a2.driver_id, a2.eta, a2.path) == ("D2", 3.0, ["N2", "N3", "N4"])
    assert a1.visited_count == 8
    assert a2.visited_count == 3
    assert a1.runtime_ms >= 0
    assert a2.runtime_ms >= 0


def test_tied_eta_uses_lexicographically_smallest_driver(tie_graph: RoadGraph) -> None:
    free_drivers = {"D9": "N1", "D10": "N2", "D2": "N3"}

    for strategy in (DijkstraPerDriver(), ReverseDijkstra()):
        result = strategy.find_driver(tie_graph, "P", free_drivers)
        assert result.driver_id == "D10"
        assert result.eta == 3.0
        assert result.path == ["N2", "P"]


def test_no_route_no_driver_and_missing_pickup(disconnected_graph: RoadGraph) -> None:
    strategies = (DijkstraPerDriver(), ReverseDijkstra())

    for strategy in strategies:
        no_route = strategy.find_driver(
            disconnected_graph, "P", {"D2": "N2", "D3": "ISOLATED"}
        )
        assert no_route.driver_id is None
        assert no_route.eta is None
        assert no_route.path is None

        no_driver = strategy.find_driver(disconnected_graph, "P", {})
        assert no_driver.driver_id is None
        assert no_driver.eta is None
        assert no_driver.visited_count == 0

        missing_pickup = strategy.find_driver(
            disconnected_graph, "missing", {"D1": "N1"}
        )
        assert missing_pickup.driver_id is None
        assert missing_pickup.eta is None


def test_a1_a2_agree_across_registered_strategies(
    small_graph: RoadGraph,
) -> None:
    assert tuple(STRATEGIES) == (
        "A1 - Dijkstra từng tài xế",
        "A2 - Dijkstra đảo chiều",
    )

    drivers = {"D1": "N1", "D2": "N2", "D3": "N5"}
    results = [
        strategy().find_driver(small_graph, "N3", drivers)
        for strategy in STRATEGIES.values()
    ]
    assert {(result.driver_id, result.eta) for result in results} == {("D2", 1.0)}


def test_zero_weight_edges_and_same_node_driver() -> None:
    graph = RoadGraph()
    graph.add_edge("N1", "P", 0)
    graph.add_node("P")

    for strategy in (DijkstraPerDriver(), ReverseDijkstra()):
        result = strategy.find_driver(graph, "P", {"D1": "N1", "D2": "P"})
        assert (result.driver_id, result.eta, result.path) == (
            "D1",
            0.0,
            ["N1", "P"],
        )

def test_a1_a2_agree_on_small_random_graphs() -> None:
    rng = random.Random(42)
    for _ in range(200):
        graph = RoadGraph()
        nodes = [f"N{i}" for i in range(1, 9)]
        for node in nodes:
            graph.add_node(node)
        for _ in range(20):
            u, v = rng.sample(nodes, 2)
            graph.add_edge(u, v, rng.randint(0, 5))

        drivers = {f"D{i}": rng.choice(nodes) for i in range(1, 4)}
        pickup = rng.choice(nodes)

        a1 = DijkstraPerDriver().find_driver(graph, pickup, drivers)
        a2 = ReverseDijkstra().find_driver(graph, pickup, drivers)
        assert (a1.driver_id, a1.eta) == (a2.driver_id, a2.eta)

def test_a1_a2_agree_on_large_random_graphs() -> None:
    num_nodes, num_edges, num_drivers, num_trials = 300, 1500, 5, 50
    nodes = [f"N{i}" for i in range(1, num_nodes + 1)]

    for seed in (7, 42, 2026):
        rng = random.Random(seed)
        for trial in range(num_trials):
            graph = RoadGraph()
            for node in nodes:
                graph.add_node(node)
            for _ in range(num_edges):
                u, v = rng.sample(nodes, 2)
                graph.add_edge(u, v, rng.randint(0, 20))

            drivers = {f"D{i}": rng.choice(nodes) for i in range(1, num_drivers + 1)}
            pickup = rng.choice(nodes)

            a1 = DijkstraPerDriver().find_driver(graph, pickup, drivers)
            a2 = ReverseDijkstra().find_driver(graph, pickup, drivers)

            assert (a1.driver_id, a1.eta) == (a2.driver_id, a2.eta), (
                f"Mismatch seed={seed}, trial={trial}: "
                f"A1={(a1.driver_id, a1.eta)}, A2={(a2.driver_id, a2.eta)}"
            )
