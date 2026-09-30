from app.knowledge.temporal_cues import (
    FUTURE_CUES,
    PAST_CUES,
    contains_cue,
    has_transition_evidence,
)
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory
from app.context.conflict_resolver import is_future_query, is_historical_query


def test_cues_match_whole_words_only():
    assert contains_cue("I will move to Pune.", FUTURE_CUES)
    assert not contains_cue("I work with William.", FUTURE_CUES)
    assert contains_cue("It was great.", PAST_CUES)
    assert not contains_cue("I visit Washington often.", PAST_CUES)


def test_multi_word_cues_match_as_phrases():
    assert contains_cue("I used to live in Mumbai.", PAST_CUES)
    assert contains_cue("I am going to relocate.", FUTURE_CUES)


def test_transition_evidence_is_word_bounded():
    assert has_transition_evidence("I moved to Pune.")
    assert has_transition_evidence("I now work at BMW.")
    assert not has_transition_evidence("I removed the old app.")


def test_name_containing_future_cue_is_not_future_fact():
    """Regression: 'will' inside 'William' previously classified the fact as FUTURE."""
    fact = extract_fact(parse_memory("I work with William."))
    assert fact is not None
    assert fact.temporal_state == "CURRENT"


def test_query_intent_cues_are_word_bounded():
    assert is_future_query("Where will I move?")
    assert is_future_query("Where am I planning to move?")
    assert not is_future_query("Where does William live?")
    assert is_historical_query("Where did I live before?")
    assert not is_historical_query("Where is Washington?")
