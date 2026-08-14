from app.graph.graph_models import GraphEdge
from app.knowledge.fact_extractor import extract_fact

RELATIONSHIP_PATTERNS = [
    ("like", "likes"),
    ("love", "likes"),
    ("enjoy", "likes"),
    ("prefer", "prefers"),
    ("study", "studies"),
    ("learn", "studies"),
    ("work", "works_at"),
    ("live", "lives_in"),
    ("own", "owns"),
    ("use", "uses"),
]


def detect_relationships(parsed_memory):
    edges = []
    content = parsed_memory.content.lower()
    fact = extract_fact(parsed_memory)

    # 1. Explicit entity relationship to user (e.g., "My friend Rahul works at Google")
    if fact and fact.relationship_to_user and fact.entity and fact.entity.lower() != "user":
        edges.append(
            GraphEdge(
                source="user",
                target=fact.entity.lower(),
                relationship=f"{fact.relationship_to_user}_of",
            )
        )

    # 2. Fact subject source resolution (user vs non-user entity)
    subject_source = "user"
    if fact and fact.entity and fact.entity.lower() != "user":
        subject_source = fact.entity.lower()

    # 3. Entity relationship detection relative to subject source
    for entity in parsed_memory.entities:
        ent_text = entity.text.lower()
        if ent_text == subject_source or ent_text == "user":
            continue
        relationship = "mentions"
        for keyword, relation in RELATIONSHIP_PATTERNS:
            if keyword in content:
                relationship = relation
                break
        edges.append(
            GraphEdge(
                source=subject_source,
                target=ent_text,
                relationship=relationship,
            )
        )

    # Fallback for entities when no fact extracted
    if not fact and not edges:
        for entity in parsed_memory.entities:
            ent_text = entity.text.lower()
            if ent_text == "user":
                continue
            edges.append(
                GraphEdge(
                    source="user",
                    target=ent_text,
                    relationship="mentions",
                )
            )

    return edges