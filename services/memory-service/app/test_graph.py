from app.understanding.memory_parser import parse_memory
from app.graph.graph_service import GraphService


def test_graph_service_processing():
    graph = GraphService()
    examples = [
        ("I like coffee.", 1),
        ("Coffee is amazing.", 2),
        ("I live in Pune.", 3),
    ]
    for text, memory_id in examples:
        parsed = parse_memory(text)
        graph.process_memory(parsed, memory_id)

    knowledge_graph = graph.repository.load()
    assert len(knowledge_graph.nodes) > 0
    assert len(knowledge_graph.edges) > 0