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
        Return graph nodes matching a keyword.
        """

        keyword = keyword.lower()

        matches = []

        for node in self.nodes:

            if keyword in node.label.lower():

                matches.append(node)

        return matches

    def memory_ids(
        self,
        keyword: str,
    ) -> list[int]:
        """
        Return all memory IDs connected to matching nodes.
        """

        ids = set()

        for node in self.search(keyword):

            ids.update(node.memory_ids)

        return sorted(ids)

    def related_nodes(
        self,
        keyword: str,
    ) -> list[GraphNode]:
        """
        Return nodes directly connected
        to the matching keyword.
        """

        keyword = keyword.lower()

        neighbors = set()

        matching = self.search(keyword)

        for node in matching:

            for edge in self.edges:

                if edge.source == node.id:

                    neighbors.add(edge.target)

                elif edge.target == node.id:

                    neighbors.add(edge.source)

        results = []

        for node in self.nodes:

            if node.id in neighbors:

                results.append(node)

        return results