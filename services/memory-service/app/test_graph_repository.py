from app.graph.graph_service import (
    GraphService,
)

from app.understanding.memory_parser import (
    parse_memory,
)

service = GraphService()

service.process_memory(

    parse_memory(
        "I like coffee."
    )

)

graph = service.process_memory(

    parse_memory(
        "I enjoy cappuccino."
    )

)

print()

print("Nodes")

for node in graph.nodes:

    print(node)

print()

print("Edges")

for edge in graph.edges:

    print(edge)