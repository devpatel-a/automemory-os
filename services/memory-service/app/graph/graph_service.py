from app.graph.graph_builder import build_graph
from app.graph.repository import GraphRepository


class GraphService:

    def __init__(self):
        self.repository = GraphRepository()

    def process_memory(
        self,
        parsed_memory,
        memory_id: int | None = None,
    ):

        graph = self.repository.load()

        new_graph = build_graph(
            parsed_memory,
            memory_id,
        )

        existing = {
            node.id.lower(): node
            for node in graph.nodes
        }

        for node in new_graph.nodes:

            current = existing.get(
                node.id.lower()
            )

            if current is None:

                graph.nodes.append(node)

                existing[node.id.lower()] = node

            else:

                for mid in node.memory_ids:

                    if mid not in current.memory_ids:

                        current.memory_ids.append(mid)

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

                existing_edges.add(key)

        self.repository.save(graph)

        return graph