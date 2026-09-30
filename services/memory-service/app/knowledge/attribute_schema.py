"""
Attribute cardinality schema.

Contradiction and supersession only make sense for *functional* (single-valued)
attributes: a person has one current residence, one current employer, one name.
Open-ended attributes (preferences, devices, tools, learning topics, activities,
verb-derived relations) legitimately hold many values at once:

    "I like coffee." + "I like tea."  -> two coexisting preferences, NOT a contradiction
    "I live in Mumbai." + "I live in Pune." -> conflicting current residence claims

This is schema knowledge about attributes, not about user values, so it stays
within the zero domain-value hard-coding rule. Unknown attributes default to
multi-valued: a missed contradiction is recoverable, a false contradiction
archives a true memory.
"""

from app.knowledge.fact_models import KnowledgeFact

SINGLE_VALUED_ATTRIBUTES = frozenset({
    "residence",
    "employer",
    "name",
    "age",
})

# Fact types produced by copular "My <noun> is <value>" and location/employment
# extraction are functional by construction.
SINGLE_VALUED_FACT_TYPES = frozenset({
    "LOCATION",
    "EMPLOYMENT",
    "PROFILE",
})

SINGLE_VALUED_ATTRIBUTE_PREFIXES = ("favorite_",)


def is_single_valued(fact: KnowledgeFact | None) -> bool:
    """True if the fact's attribute can hold only one current value per entity."""
    if fact is None or not fact.attribute:
        return False
    attribute = fact.attribute.strip().lower()
    return (
        attribute in SINGLE_VALUED_ATTRIBUTES
        or attribute.startswith(SINGLE_VALUED_ATTRIBUTE_PREFIXES)
        or fact.fact_type in SINGLE_VALUED_FACT_TYPES
    )


def fact_domain_key(fact: KnowledgeFact) -> tuple:
    """
    Key under which facts compete for a single answer slot.

    Single-valued attributes compete per (entity, attribute); multi-valued
    attributes compete per (entity, attribute, value) so that coexisting values
    are never collapsed into one.
    """
    base = (fact.entity.strip().lower(), fact.attribute.strip().lower())
    if is_single_valued(fact):
        return base
    return base + (fact.value.strip().lower(),)
