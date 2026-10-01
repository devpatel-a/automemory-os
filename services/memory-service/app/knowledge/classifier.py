from app.knowledge.knowledge_types import KnowledgeDecision
from app.knowledge.result_models import KnowledgeResult
from app.knowledge.temporal_cues import has_transition_evidence
from app.knowledge.attribute_schema import is_single_valued
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.contradiction_detector import detect_contradiction
from app.understanding.memory_parser import parse_memory


def get_memory_object(item):
    if hasattr(item, "content"):
        return item
    if hasattr(item, "__getitem__"):
        return item[0]
    return item


def is_merge_equivalent(new_parsed, existing_mem, distance=None) -> bool:
    if detect_contradiction(new_parsed, existing_mem):
        return False

    if not hasattr(existing_mem, "content"):
        return False

    existing_content = existing_mem.content.strip().lower()
    new_content = new_parsed.content.strip().lower()

    if new_content == existing_content:
        return True

    existing_parsed = parse_memory(existing_mem.content)
    new_fact = extract_fact(new_parsed)
    existing_fact = extract_fact(existing_parsed)

    # MERGE only if entity, attribute, value match and neither is negated
    if new_fact and existing_fact and new_fact.attribute and existing_fact.attribute:
        norm_n_ent = new_fact.entity.strip().lower()
        norm_n_attr = new_fact.attribute.strip().lower()
        norm_n_val = new_fact.value.strip().lower()

        norm_e_ent = existing_fact.entity.strip().lower()
        norm_e_attr = existing_fact.attribute.strip().lower()
        norm_e_val = existing_fact.value.strip().lower()

        if norm_n_ent == norm_e_ent and norm_n_attr == norm_e_attr:
            if new_fact.is_negated or existing_fact.is_negated:
                return False
            # A plan and the fact that fulfils it are different facts: never
            # merge a FUTURE fact with a non-FUTURE one (fulfilment is linked
            # as lineage instead, see MemoryPipeline).
            if (new_fact.temporal_state == "FUTURE") != (existing_fact.temporal_state == "FUTURE"):
                return False
            return norm_n_val == norm_e_val
        else:
            return False

    if (
        hasattr(new_parsed, "category")
        and hasattr(existing_parsed, "category")
        and new_parsed.category != existing_parsed.category
    ):
        return False

    if distance is not None and distance >= 0.08:
        return False

    tokens_new = set(new_content.split())
    tokens_ex = set(existing_content.split())
    if not tokens_new or not tokens_ex:
        return False

    jaccard = len(tokens_new.intersection(tokens_ex)) / float(
        len(tokens_new.union(tokens_ex))
    )

    return jaccard >= 0.35


def _distance(item):
    return item[1] if hasattr(item, "__getitem__") and len(item) > 1 else None


def assess_knowledge(
    parsed_memory,
    candidates,
    historical_ids=frozenset(),
) -> KnowledgeResult:
    """
    Classify incoming knowledge against candidate memories.

    Returns the decision together with the exact target memory the decision
    applies to and machine-readable reason codes, so executors never have to
    re-derive (and possibly mis-derive) the target.

    historical_ids: candidate ids with historical lineage (superseded_by /
    fulfilled_by). They describe the past and never compete with incoming
    current facts, so they are neither contradicted nor superseded again.
    """
    new_fact = extract_fact(parsed_memory) if parsed_memory is not None else None

    def result(decision, target=None, *reasons):
        return KnowledgeResult(
            fact=new_fact,
            decision=decision,
            target_memory_id=getattr(target, "id", None) if target is not None else None,
            reason_codes=list(reasons),
        )

    if not candidates:
        return result(KnowledgeDecision.NEW, None, "no_candidates")

    live = [
        item for item in candidates
        if getattr(get_memory_object(item), "id", None) not in historical_ids
    ]

    if new_fact is not None and new_fact.attribute:
        norm_entity = new_fact.entity.strip().lower()
        norm_attribute = new_fact.attribute.strip().lower()
        norm_value = new_fact.value.strip().lower()
        incoming_temporal = new_fact.temporal_state
        content_lower = parsed_memory.content.lower()
        cardinality = "single_valued_attribute" if is_single_valued(new_fact) else "multi_valued_attribute"

        for item in live:
            cand_mem = get_memory_object(item)
            if not hasattr(cand_mem, "content"):
                continue
            existing_fact = extract_fact(parse_memory(cand_mem.content))
            if existing_fact is None or not existing_fact.attribute:
                continue
            ex_value = existing_fact.value.strip().lower()
            existing_temporal = existing_fact.temporal_state

            if not (
                existing_fact.entity.strip().lower() == norm_entity
                and existing_fact.attribute.strip().lower() == norm_attribute
            ):
                continue

            # Rule G: Negated statement ("I do not live in Mumbai anymore")
            if new_fact.is_negated and ex_value == norm_value:
                return result(
                    KnowledgeDecision.SUPERSESSION, cand_mem,
                    "same_entity", "same_attribute", "same_value", "negation_detected",
                )

            # Rule A: Same value -> continue to MERGE/REINFORCEMENT
            if ex_value == norm_value:
                continue

            # Multi-valued attributes (preferences, devices, tools, ...)
            # hold several values at once: different values coexist.
            if not is_single_valued(new_fact):
                continue

            # Rule E & F: Incoming FUTURE fact -> PRESERVE BOTH (NEW)
            if incoming_temporal == "FUTURE":
                continue

            # A stored plan is not a current claim: never supersede
            # or contradict FUTURE facts with a different value.
            if existing_temporal == "FUTURE":
                continue

            # Explicit transition evidence -> SUPERSESSION
            if has_transition_evidence(content_lower):
                return result(
                    KnowledgeDecision.SUPERSESSION, cand_mem,
                    "same_entity", "same_attribute", "different_value", cardinality,
                    "transition_detected",
                )

            # Rule B: Existing HISTORICAL + Incoming CURRENT -> SUPERSESSION
            if existing_temporal == "HISTORICAL" and incoming_temporal == "CURRENT":
                return result(
                    KnowledgeDecision.SUPERSESSION, cand_mem,
                    "same_entity", "same_attribute", "different_value", cardinality,
                    "historical_to_current",
                )

            # Rule D: Existing CURRENT + Incoming CURRENT + NO transition evidence -> CONTRADICTION
            if incoming_temporal == "CURRENT":
                return result(
                    KnowledgeDecision.CONTRADICTION, cand_mem,
                    "same_entity", "same_attribute", "different_value", cardinality,
                    "conflicting_current_claims", "no_transition_evidence",
                )

    # Check for MERGE / REINFORCEMENT (never against historical memories)
    if parsed_memory is not None:
        for item in live:
            cand_mem = get_memory_object(item)
            if is_merge_equivalent(parsed_memory, cand_mem, distance=_distance(item)):
                if (
                    hasattr(cand_mem, "content")
                    and parsed_memory.content.strip().lower()
                    == cand_mem.content.strip().lower()
                ):
                    return result(KnowledgeDecision.REINFORCEMENT, cand_mem, "exact_content_match")
                return result(KnowledgeDecision.MERGE, cand_mem, "equivalent_fact")

    if not live:
        return result(KnowledgeDecision.NEW, None, "only_historical_candidates")

    # Distance classification against the best live candidate
    best_cand = live[0]
    distance = _distance(best_cand)

    if distance is None:
        return result(KnowledgeDecision.NEW, None, "no_semantic_distance")

    if distance < 0.10:
        return result(
            KnowledgeDecision.REINFORCEMENT, get_memory_object(best_cand), "semantic_near_duplicate",
        )

    if distance < 0.35:
        return result(KnowledgeDecision.RELATED, get_memory_object(best_cand), "semantically_related")

    return result(KnowledgeDecision.NEW, None, "no_structured_or_semantic_match")


def classify_knowledge(
    parsed_memory,
    candidates,
    historical_ids=frozenset(),
):
    """Backward-compatible wrapper returning only the KnowledgeDecision."""
    return assess_knowledge(parsed_memory, candidates, historical_ids).decision
