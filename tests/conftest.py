import pytest

from core.road_graph import RoadGraph


@pytest.fixture
def small_graph() -> RoadGraph:
    graph = RoadGraph()
    graph.add_edge("N1", "N2", 2)
    graph.add_edge("N1", "N3", 6)
    graph.add_edge("N2", "N3", 1)
    graph.add_edge("N2", "N4", 4)
    graph.add_edge("N3", "N4", 2)
    graph.add_node("N5")
    return graph


@pytest.fixture
def tie_graph() -> RoadGraph:
    graph = RoadGraph()
    graph.add_edge("N1", "P", 3)
    graph.add_edge("N2", "P", 3)
    graph.add_edge("N3", "P", 5)
    return graph


@pytest.fixture
def disconnected_graph() -> RoadGraph:
    graph = RoadGraph()
    graph.add_edge("N1", "P", 2)
    graph.add_edge("N2", "N3", 1)
    graph.add_node("ISOLATED")
    graph.add_node("P")
    return graph
