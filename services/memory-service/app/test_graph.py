from app.understanding.memory_parser import parse_memory
from app.graph.graph_service import GraphService

graph = GraphService()

examples = [
    ("I like coffee.", 1),
    ("Coffee is amazing.", 2),
    ("I live in Pune.", 3),
]

for text, memory_id in examples:

    parsed = parse_memory(text)

    graph.process_memory(
        parsed,
        memory_id,
    )

knowledge_graph = graph.repository.load()

print("\nNodes")

for node in knowledge_graph.nodes:
    print(node)

print("\nEdges")

for edge in knowledge_graph.edges:
    print(edge)