from app.graph.graph_builder import build_graph


class GraphService:
    """
    Coordinates Knowledge Graph operations.
    """

    def process_memory(
        self,
        parsed_memory,
    ):
        graph = build_graph(parsed_memory)

        return graph