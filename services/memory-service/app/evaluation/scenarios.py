"""
Synthetic but realistic multi-message benchmark scenarios.

Each scenario ingests statements through the real MemoryPipeline, then checks
context retrieval (ranking metrics), evolution lineage (contradiction /
supersession pairs), graph edges and duplicate suppression against labels.

Labels refer to memories by their exact statement text.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryCase:
    query: str
    # Statements that answer the query (binary relevance).
    relevant: tuple[str, ...]
    # Statements that must NOT be selected (e.g. a plan for a current question).
    forbidden: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    name: str
    statements: tuple[tuple[str, str], ...]  # (text, category)
    queries: tuple[QueryCase, ...] = ()
    # (older statement, newer statement) lineage pairs expected in the final state
    superseded: tuple[tuple[str, str], ...] = ()
    contradicted: tuple[tuple[str, str], ...] = ()
    # (source, relationship, target), lower-case graph node ids
    edges_present: tuple[tuple[str, str, str], ...] = ()
    edges_absent: tuple[tuple[str, str, str], ...] = ()
    # (entity, attribute, value) facts that must have exactly one live memory
    canonical_facts: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class ExtractionCase:
    text: str
    entity: str
    attribute: str
    value: str
    temporal_state: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="residence_timeline",
        statements=(
            ("I live in Mumbai.", "profile"),
            ("I moved to Pune.", "profile"),
            ("I am planning to move to Bangalore.", "profile"),
        ),
        queries=(
            QueryCase("What city do I live in?", ("I moved to Pune.",),
                      forbidden=("I am planning to move to Bangalore.",)),
            QueryCase("Where did I live before?", ("I live in Mumbai.",)),
            QueryCase("Where am I planning to move?", ("I am planning to move to Bangalore.",)),
        ),
        superseded=(("I live in Mumbai.", "I moved to Pune."),),
    ),
    Scenario(
        name="long_residence_timeline",
        statements=(
            ("I lived in Delhi.", "profile"),
            ("I live in Mumbai.", "profile"),
            ("I moved to Pune.", "profile"),
            ("I will move to Bangalore next month.", "profile"),
        ),
        queries=(
            QueryCase("Where do I live?", ("I moved to Pune.",),
                      forbidden=("I will move to Bangalore next month.",)),
            QueryCase("Where did I live before?", ("I lived in Delhi.", "I live in Mumbai.")),
            QueryCase("Where will I move?", ("I will move to Bangalore next month.",)),
        ),
        superseded=(
            ("I lived in Delhi.", "I live in Mumbai."),
            ("I live in Mumbai.", "I moved to Pune."),
        ),
    ),
    Scenario(
        name="residence_contradiction",
        statements=(
            ("I live in Mumbai.", "profile"),
            ("I live in Pune.", "profile"),
        ),
        queries=(
            QueryCase("Where do I live?", ("I live in Pune.",), forbidden=("I live in Mumbai.",)),
        ),
        contradicted=(("I live in Mumbai.", "I live in Pune."),),
    ),
    Scenario(
        name="residence_reassertion",
        statements=(
            ("I live in Mumbai.", "fact"),
            ("I live in Pune.", "fact"),
            ("I live in Mumbai.", "fact"),
        ),
        queries=(
            QueryCase("Where do I live?", ("I live in Mumbai.",), forbidden=("I live in Pune.",)),
        ),
        contradicted=(("I live in Pune.", "I live in Mumbai."),),
        canonical_facts=(("user", "residence", "mumbai"),),
    ),
    Scenario(
        name="employment_transition",
        statements=(
            ("I work at Google.", "profile"),
            ("I now work at BMW.", "profile"),
        ),
        queries=(
            QueryCase("Where do I work?", ("I now work at BMW.",), forbidden=("I work at Google.",)),
            QueryCase("Where did I work before?", ("I work at Google.",)),
        ),
        superseded=(("I work at Google.", "I now work at BMW."),),
    ),
    Scenario(
        name="negated_residence",
        statements=(
            ("I live in Mumbai.", "profile"),
            ("I do not live in Mumbai anymore.", "profile"),
        ),
        superseded=(("I live in Mumbai.", "I do not live in Mumbai anymore."),),
    ),
    Scenario(
        name="entity_separation",
        statements=(
            ("My friend Rahul works at Google.", "fact"),
            ("Rahul Patel lives in Delhi.", "fact"),
            ("Rahul Sharma works at BMW.", "fact"),
        ),
        queries=(
            QueryCase("Where does Rahul Sharma work?", ("Rahul Sharma works at BMW.",)),
            QueryCase("Where does Rahul Patel live?", ("Rahul Patel lives in Delhi.",)),
        ),
        edges_present=(
            ("user", "friend_of", "rahul"),
            ("rahul", "works_at", "google"),
            ("rahul patel", "lives_in", "delhi"),
            ("rahul sharma", "works_at", "bmw"),
        ),
        edges_absent=(
            ("user", "works_at", "google"),
            ("user", "works_with", "rahul"),
            ("user", "works_at", "bmw"),
            ("user", "lives_in", "delhi"),
        ),
    ),
    Scenario(
        name="device_reinforcement",
        statements=(
            ("I use a MacBook Air.", "fact"),
            ("I primarily work on my MacBook Air.", "fact"),
            ("I use my MacBook Air for development.", "fact"),
        ),
        canonical_facts=(("user", "device", "macbook air"),),
    ),
    Scenario(
        name="coexisting_preferences",
        statements=(
            ("I like coffee.", "preference"),
            ("I like tea.", "preference"),
        ),
        queries=(
            QueryCase("What do I like?", ("I like coffee.", "I like tea.")),
        ),
    ),
    Scenario(
        name="repeated_low_importance_fact",
        statements=(
            ("I live in Pune.", "fact"),
            ("I live in Pune.", "fact"),
        ),
        queries=(
            QueryCase("Where do I live?", ("I live in Pune.",)),
        ),
        canonical_facts=(("user", "residence", "pune"),),
    ),
)


EXTRACTION_CASES: tuple[ExtractionCase, ...] = (
    ExtractionCase("I live in Pune.", "user", "residence", "Pune", "CURRENT"),
    ExtractionCase("I used to live in Mumbai.", "user", "residence", "Mumbai", "HISTORICAL"),
    ExtractionCase("I lived in Delhi.", "user", "residence", "Delhi", "HISTORICAL"),
    ExtractionCase("I moved to Pune.", "user", "residence", "Pune", "CURRENT"),
    ExtractionCase("I will move to Bangalore.", "user", "residence", "Bangalore", "FUTURE"),
    ExtractionCase("I am planning to move to Bangalore.", "user", "residence", "Bangalore", "FUTURE"),
    ExtractionCase("I work at Google.", "user", "employer", "Google", "CURRENT"),
    ExtractionCase("I now work at BMW.", "user", "employer", "BMW", "CURRENT"),
    ExtractionCase("I worked at Infosys.", "user", "employer", "Infosys", "HISTORICAL"),
    ExtractionCase("I work with William.", "user", "work_with", "William", "CURRENT"),
    ExtractionCase("My friend Rahul works at Google.", "Rahul", "employer", "Google", "CURRENT"),
    ExtractionCase("Rahul Sharma works at BMW.", "Rahul Sharma", "employer", "BMW", "CURRENT"),
    ExtractionCase("I like coffee in the morning.", "user", "preference", "coffee", "CURRENT"),
    ExtractionCase("I prefer espresso.", "user", "preference", "espresso", "CURRENT"),
    ExtractionCase("I use my MacBook Air for development.", "user", "device", "MacBook Air", "CURRENT"),
    ExtractionCase("I use Python for work.", "user", "tool", "Python", "CURRENT"),
    ExtractionCase("I am learning FastAPI.", "user", "learning_topic", "FastAPI", "CURRENT"),
    ExtractionCase("My favorite drink is coffee.", "user", "favorite_drink", "coffee", "CURRENT"),
    ExtractionCase("I do not live in Mumbai anymore.", "user", "residence", "Mumbai", "HISTORICAL"),
    # Known limitation (docs/KNOWN_LIMITATIONS.md): multi-event narratives are
    # reduced to one primary fact; labelled with the ideal primary fact.
    ExtractionCase("Before living in Mumbai, I lived in Pune.", "user", "residence", "Pune", "HISTORICAL"),
)
