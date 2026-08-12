from app.graph.graph_service import GraphService
from app.understanding.memory_parser import parse_memory


def test_graph_repository_saving():
    service = GraphService()
    service.process_memory(parse_memory("I like coffee."))
    graph = service.process_memory(parse_memory("I enjoy cappuccino."))
    assert len(graph.nodes) > 0