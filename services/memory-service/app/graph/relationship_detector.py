from app.graph.graph_models import GraphEdge


RELATIONSHIP_PATTERNS = [

    ("like", "likes"),
    ("love", "likes"),
    ("enjoy", "likes"),
    ("prefer", "prefers"),
    ("study", "studies"),
    ("learn", "studies"),
    ("work", "works_with"),
    ("live", "lives_in"),
    ("own", "owns"),
    ("use", "uses"),
]


def detect_relationships(parsed_memory):

    edges = []

    content = parsed_memory.content.lower()

    for entity in parsed_memory.entities:

        relationship = "mentions"

        for keyword, relation in RELATIONSHIP_PATTERNS:

            if keyword in content:
                relationship = relation
                break

        edges.append(

            GraphEdge(

                source="user",

                target=entity.text.lower(),

                relationship=relationship,

            )

        )

    return edges