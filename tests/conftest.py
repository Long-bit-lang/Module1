import pytest

from core.road_graph import RoadGraph

try:
    from streamlit.runtime.state.safe_session_state import SafeSessionState
    from streamlit.testing.v1 import AppTest
    from streamlit.testing.v1.element_tree import Block

    if not hasattr(SafeSessionState, "get"):
        SafeSessionState.get = lambda self, k, d=None: self[k] if k in self else d

    def _block_key(self):
        if hasattr(self, "proto") and hasattr(self.proto, "id"):
            raw_id = self.proto.id
            if "-" in raw_id:
                return raw_id.split("-", 2)[-1]
        return None

    Block.key = property(_block_key)

    def _get_containers(self):
        results = []

        def _walk(node):
            if hasattr(node, "children"):
                children = (
                    node.children.values()
                    if isinstance(node.children, dict)
                    else node.children
                )
                for child in children:
                    if isinstance(child, Block):
                        results.append(child)
                    _walk(child)

        for root in (getattr(self, "main", None), getattr(self, "sidebar", None)):
            if root:
                _walk(root)
        return results

    if not hasattr(AppTest, "container"):
        AppTest.container = property(_get_containers)
except ImportError:
    pass



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
