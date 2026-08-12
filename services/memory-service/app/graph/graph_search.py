from app.graph.graph_models import (
    GraphNode,
    GraphEdge,
)


class GraphSearch:
    """
    Search the in-memory knowledge graph.
    """

    def __init__(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ):
        self.nodes = nodes
        self.edges = edges

    def search(
        self,
        keyword: str,
    ) -> list[GraphNode]:
        """
        Return all nodes matching a keyword.
        """

        keyword = keyword.lower()

        matches = []

        for node in self.nodes:

            if keyword in node.label.lower():

                matches.append(node)

        return matches