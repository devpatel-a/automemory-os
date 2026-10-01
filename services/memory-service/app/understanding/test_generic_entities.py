"""
Entity extraction is value-agnostic: unseen names, products, places, topics
and books are extracted exactly like familiar ones, without a curated list.
"""

import pytest

import app.understanding.memory_entity_extractor as extractor_module
from app.understanding.entity_normalizer import normalize_entity_name
from app.understanding.memory_entity_extractor import extract_memory_entities
from app.understanding.memory_parser import parse_memory


def names(text):
    return {normalize_entity_name(e.text) for e in parse_memory(text).entities}


def test_no_curated_keyword_list_remains():
    assert not hasattr(extractor_module, "MEMORY_KEYWORDS")


@pytest.mark.parametrize("statement, expected", [
    ("I work at BMW.", "bmw"),
    ("I work at Microsoft.", "microsoft"),
    ("I like coffee.", "coffee"),
    ("I live in Ahmedabad.", "ahmedabad"),
    ("I study quantum computing.", "quantum computing"),
    ("I invested in Zyntrexa Labs.", "zyntrexa labs"),
    ("My mentor is Oluwaseun Adeyemi.", "oluwaseun adeyemi"),
    ("I am reading Snow Crash.", "snow crash"),
    ("I program in Zig.", "zig"),
    ("I drink kombucha every morning.", "kombucha"),
])
def test_unseen_entities_are_extracted(statement, expected):
    assert expected in names(statement)


def test_noun_chunk_entities_are_normalized_and_pronouns_skipped():
    texts = {e.text for e in extract_memory_entities("I use my MacBook Air for this and that.")}
    assert "macbook air" in texts
    assert not texts & {"i", "my", "this", "that"}


def test_entity_names_are_never_shortened():
    assert normalize_entity_name("Rahul Patel") == "rahul patel"
    assert normalize_entity_name("Rahul Patel") != normalize_entity_name("Rahul Sharma")
    assert normalize_entity_name("the Morning") == "morning"
