from app.graph.graph_models import (
    GraphNode,
    KnowledgeGraph,
)

from app.graph.relationship_detector import (
    detect_relationships,
)


def build_graph(
    parsed_memory,
    memory_id: int | None = None,
) -> KnowledgeGraph:
    """
    Build a graph from ParsedMemory.
    """

    nodes = []

    seen = set()

    for entity in parsed_memory.entities:

        node_id = entity.text.lower()

        if node_id in seen:
            continue

        seen.add(node_id)

        nodes.append(
            GraphNode(
                id=node_id,
                label=entity.text,
                type=entity.label,
                memory_ids=[] if memory_id is None else [memory_id],
            )
        )

    edges = detect_relationships(
        parsed_memory,
    )

    return KnowledgeGraph(
        nodes=nodes,
        edges=edges,
    )