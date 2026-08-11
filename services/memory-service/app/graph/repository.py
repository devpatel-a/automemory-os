from app.graph.graph_models import (
    KnowledgeGraph,
)


class GraphRepository:
    """
    Temporary in-memory graph repository.

    Later this will be backed by PostgreSQL.
    """

    def __init__(self):

        self.graph = KnowledgeGraph(
            nodes=[],
            edges=[],
        )

    def load(self):

        return self.graph

    def save(
        self,
        graph: KnowledgeGraph,
    ):

        self.graph = graph