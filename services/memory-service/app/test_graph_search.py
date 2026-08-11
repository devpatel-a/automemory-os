from app.graph.graph_models import (
    GraphNode,
    GraphEdge,
    KnowledgeGraph,
)

from app.graph.graph_search import (
    expand_context,
)

graph = KnowledgeGraph(

    nodes=[

        GraphNode(
            id="coffee",
            label="Coffee",
            type="drink",
        ),

        GraphNode(
            id="cappuccino",
            label="Cappuccino",
            type="drink",
        ),

        GraphNode(
            id="starbucks",
            label="Starbucks",
            type="company",
        ),

    ],

    edges=[

        GraphEdge(
            source="coffee",
            target="cappuccino",
            relationship="related",
        ),

        GraphEdge(
            source="cappuccino",
            target="starbucks",
            relationship="served_at",
        ),

    ],

)

expanded = expand_context(
    ["coffee"],
    graph,
)

print(expanded)