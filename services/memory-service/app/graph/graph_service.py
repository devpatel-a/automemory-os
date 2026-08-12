from app.graph.graph_builder import build_graph
from app.graph.repository import GraphRepository


class GraphService:
    """
    Handles updates to the in-memory Knowledge Graph.
    """

    def __init__(self):
        self.repository = GraphRepository()

    def process_memory(
        self,
        parsed_memory,
    ):
        graph = self.repository.load()

        new_graph = build_graph(parsed_memory)

        # -----------------------------
        # Merge Nodes
        # -----------------------------
        existing_nodes = {
            node.id.lower(): node
            for node in graph.nodes
        }

        for node in new_graph.nodes:

            if node.id.lower() not in existing_nodes:

                graph.nodes.append(node)

        # -----------------------------
        # Merge Edges
        # -----------------------------
        existing_edges = {
            (
                edge.source.lower(),
                edge.target.lower(),
                edge.relationship.lower(),
            )
            for edge in graph.edges
        }

        for edge in new_graph.edges:

            key = (
                edge.source.lower(),
                edge.target.lower(),
                edge.relationship.lower(),
            )

            if key not in existing_edges:

                graph.edges.append(edge)

        self.repository.save(graph)

        return graph