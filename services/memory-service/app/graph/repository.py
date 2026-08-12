from app.graph.graph_models import (
    KnowledgeGraph,
)

# Process-local in-memory graph state for AutoMemory OS v1.
# All GraphService instances within the same Python process load and save to this shared graph.
_shared_graph = KnowledgeGraph(
    nodes=[],
    edges=[],
)


def reset_shared_graph():
    """Reset process-shared in-memory KnowledgeGraph for test isolation."""
    global _shared_graph
    _shared_graph = KnowledgeGraph(
        nodes=[],
        edges=[],
    )


class GraphRepository:
    """
    Process-local in-memory graph repository for AutoMemory OS v1.

    Multiple GraphService instances within the same process share the KnowledgeGraph state.
    """

    def load(self) -> KnowledgeGraph:
        return _shared_graph

    def save(
        self,
        graph: KnowledgeGraph,
    ):
        global _shared_graph
        _shared_graph = graph

    def reset(self):
        reset_shared_graph()