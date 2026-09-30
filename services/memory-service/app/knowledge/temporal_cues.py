"""
Centralized linguistic temporal cues.

Single source of truth for the temporal keyword baseline used by fact extraction,
knowledge classification, contradiction detection and query-intent detection.

All matching is whole-word / whole-phrase (regex word boundaries), so that e.g.
"will" does not match "William", "was" does not match "Washington" and
"moved" does not match "removed".

These are generic linguistic markers (tense, aspect, transition, intention),
never domain values.
"""

import re
from functools import lru_cache
from typing import Iterable

# Statement-level cues
PAST_CUES = frozenset({
    "lived", "worked", "was", "used to", "previously", "formerly",
    "before", "earlier", "last year",
})

FUTURE_CUES = frozenset({
    "will", "going to", "tomorrow", "next", "future",
})

# Explicit state-transition evidence ("I moved to Pune" supersedes "I live in Mumbai")
TRANSITION_CUES = frozenset({
    "moved to", "moved", "changed to", "transferred to", "transferred",
    "now live", "now work", "relocated to", "relocated",
})

# Verbs whose open clausal complement describes a planned (FUTURE) state:
# "I am planning to move to Bangalore" -> residence(Bangalore) FUTURE
INTENTION_VERB_LEMMAS = frozenset({
    "plan", "intend", "expect", "aim", "schedule", "prepare",
})

NEGATION_TRANSITION_CUES = frozenset({"anymore", "no longer", "longer"})

# Query-level cues
HISTORICAL_QUERY_CUES = frozenset({
    "before", "previously", "past", "history", "used to", "formerly",
    "lived in", "was", "earlier", "did i",
})

FUTURE_QUERY_CUES = frozenset({
    "will", "going to", "future", "next year", "tomorrow", "plan to",
    "planning", "plan", "plans", "planned", "intend", "intending",
})


@lru_cache(maxsize=None)
def _compile(cues: frozenset) -> re.Pattern:
    # Longest phrases first so multi-word cues win over their prefixes.
    alternatives = sorted(cues, key=len, reverse=True)
    return re.compile(
        r"\b(?:" + "|".join(re.escape(c) for c in alternatives) + r")\b",
        re.IGNORECASE,
    )


def contains_cue(text: str, cues: Iterable[str]) -> bool:
    """Whole-word / whole-phrase cue match (case-insensitive)."""
    if not text:
        return False
    return _compile(frozenset(cues)).search(text) is not None


def has_transition_evidence(text: str) -> bool:
    """True when text explicitly describes a state transition ("moved to", "now work", ...)."""
    return contains_cue(text, TRANSITION_CUES)
