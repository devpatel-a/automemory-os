from app.context.models import ContextCandidate
from app.context.entity_matcher import entity_match_score
from app.context.temporal_matcher import temporal_match_score
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory


def evaluate_evidence(
    candidate: ContextCandidate,
    query: str,
    query_entities: list,
) -> ContextCandidate:
    """
    Evaluates evidence strength of a retrieved candidate for answering query.

    Authoritative Context Evidence Score Formula:
        final_evidence_score = base_retrieval_score
                             + entity_match_bonus
                             + fact_attribute_match_bonus
                             + temporal_intent_bonus

    Zero domain-specific hardcoded string rules (e.g. coffee, espresso, cities).
    Uses structured KnowledgeFact attribute and entity signals.
    """
    memory = candidate.memory

    explanation = []

    # 1. Base Retrieval Score (Reuses normalized hybrid retrieval score)
    base_score = (
        candidate.similarity if candidate.similarity is not None else 0.5
    )
    explanation.append(f"base_retrieval_score: {base_score:.3f}")

    # 2. Entity Match Bonus (Exact query entity matches vs weak substring overlap)
    ent_bonus = entity_match_score(query_entities, memory.content)
    if ent_bonus > 0:
        explanation.append(f"entity_match_bonus: +{ent_bonus:.3f}")

    # 3. Fact Attribute Match Bonus (Generic structured fact matching)
    fact_bonus = 0.0
    parsed_query = parse_memory(query)
    query_fact = extract_fact(parsed_query)

    parsed_mem = parse_memory(memory.content)
    mem_fact = extract_fact(parsed_mem)

    if query_fact and mem_fact and query_fact.attribute and mem_fact.attribute:
        if (
            query_fact.entity.lower() == mem_fact.entity.lower()
            and query_fact.attribute.lower() == mem_fact.attribute.lower()
        ):
            fact_bonus = 0.35
            explanation.append(
                f"fact_attribute_match ({query_fact.attribute}): +0.350"
            )
        elif query_fact.attribute.lower() in mem_fact.attribute.lower():
            fact_bonus = 0.20
            explanation.append(
                f"fact_attribute_partial_match ({query_fact.attribute}): +0.200"
            )
    elif query_fact and query_fact.attribute:
        # Check if extracted query attribute term matches memory content generically
        attr_term = query_fact.attribute.lower()
        if attr_term in memory.content.lower():
            fact_bonus = 0.15
            explanation.append(f"fact_attribute_term_match ({attr_term}): +0.150")

    # 4. Temporal Intent Bonus
    temp_bonus = temporal_match_score(query, memory.content)
    if temp_bonus > 0:
        explanation.append(f"temporal_intent_bonus: +{temp_bonus:.3f}")

    final_evidence_score = (
        base_score
        + ent_bonus
        + fact_bonus
        + temp_bonus
    )

    if candidate.retrieval is not None:
        candidate.retrieval.entity_score = ent_bonus
        candidate.retrieval.attribute_score = fact_bonus
        candidate.retrieval.temporal_score = temp_bonus
        candidate.retrieval.final_score = final_evidence_score

    candidate.score = final_evidence_score
    candidate.evidence_score = final_evidence_score
    candidate.explanation = explanation
    return candidate
