from app.graph.graph_models import (
    KnowledgeGraph,
)


def expand_context(
    query_entities: list[str],
    graph: KnowledgeGraph,
) -> list[str]:
    """
    Expand query entities using the KnowledgeGraph.
    """

    return graph.expand(
        query_entities,
    )