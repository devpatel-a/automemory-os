from app.graph.graph_builder import (
    build_graph,
)

from app.graph.repository import (
    GraphRepository,
)


class GraphService:

    def __init__(self):

        self.repository = GraphRepository()

    def process_memory(
        self,
        parsed_memory,
    ):

        existing_graph = self.repository.load()

        new_graph = build_graph(
            parsed_memory,
        )

        existing_graph.nodes.extend(
            new_graph.nodes,
        )

        existing_graph.edges.extend(
            new_graph.edges,
        )

        self.repository.save(
            existing_graph,
        )

        return existing_graph