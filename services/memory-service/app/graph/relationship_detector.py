from app.graph.graph_models import GraphEdge
from app.knowledge.fact_extractor import extract_fact
from app.nlp import parse_text
from app.understanding.entity_normalizer import normalize_entity_name

# Verb lemma -> relationship type (matched on lemmas, never substrings:
# "because" does not contain the verb "use").
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

MENTIONS = "mentions"


def _relationship_for(parsed_memory, fact) -> str:
    lemmas = {t.lemma_.lower() for t in parse_text(parsed_memory.content) if t.pos_ in ("VERB", "AUX")}
    if fact is not None and fact.attribute and fact.attribute.startswith("work_"):
        # "work on X" / "work with X" are not employment.
        return fact.attribute
    for lemma, relation in RELATIONSHIP_PATTERNS:
        if lemma in lemmas:
            return relation
    return MENTIONS


def detect_relationships(parsed_memory):
    """
    Typed edges for one memory, using normalized entity names as endpoints.

    - explicit relationship to the user ("My friend Rahul ...") -> user --friend_of--> rahul
    - the fact's subject (user or a named entity) --relation--> the fact's value
    - every other entity the sentence mentions -> subject --mentions--> entity
    Subjects are never re-attributed to the user ("Rahul works at Google"
    creates rahul --works_at--> google, not user --works_at--> google).
    """
    edges = []
    fact = extract_fact(parsed_memory)

    subject_source = "user"
    if fact and fact.entity and fact.entity.lower() != "user":
        subject_source = normalize_entity_name(fact.entity)

    # 1. Explicit entity relationship to user (e.g., "My friend Rahul works at Google")
    if fact and fact.relationship_to_user and subject_source != "user":
        edges.append(GraphEdge(
            source="user",
            target=subject_source,
            relationship=f"{fact.relationship_to_user}_of",
        ))

    value_key = normalize_entity_name(fact.value) if fact and fact.value else ""
    relation = _relationship_for(parsed_memory, fact)

    # 2. Subject -> entities, typed only for the fact's value
    for entity in parsed_memory.entities:
        ent_key = normalize_entity_name(entity.text)
        if not ent_key or ent_key in (subject_source, "user"):
            continue
        edges.append(GraphEdge(
            source=subject_source,
            target=ent_key,
            relationship=relation if ent_key == value_key else MENTIONS,
        ))

    return edges
