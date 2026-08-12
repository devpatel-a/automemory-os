from app.graph.graph_models import GraphNode, GraphEdge
from app.graph.graph_search import GraphSearch


def test_graph_search():
    nodes = [
        GraphNode(id="coffee", label="Coffee", type="drink"),
        GraphNode(id="pune", label="Pune", type="location"),
    ]
    edges = [
        GraphEdge(source="user", target="coffee", relationship="likes"),
        GraphEdge(source="user", target="pune", relationship="lives_in"),
    ]
    graph = GraphSearch(nodes, edges)
    matches = graph.search("coffee")
    assert len(matches) == 1
    assert matches[0].id == "coffee"