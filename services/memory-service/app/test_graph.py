from app.understanding.memory_parser import (
    parse_memory,
)

from app.graph.graph_builder import (
    build_graph,
)

examples = [

    "I like coffee.",

    "I live in Pune.",

    "I study Python.",

    "I own a Tesla.",

]

for sentence in examples:

    print("\n", "=" * 50)

    print(sentence)

    parsed = parse_memory(sentence)

    graph = build_graph(parsed)

    for edge in graph.edges:
        print(edge)