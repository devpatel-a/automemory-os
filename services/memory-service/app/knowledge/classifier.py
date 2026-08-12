from app.knowledge.knowledge_types import KnowledgeDecision
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
    # 1. Contradiction check: never merge contradictions
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

    # 2. Structured Facts Check: MERGE only if entity, attribute, and value match
    if new_fact and existing_fact:
        norm_n_ent = new_fact.entity.strip().lower()
        norm_n_attr = new_fact.attribute.strip().lower()
        norm_n_val = new_fact.value.strip().lower()

        norm_e_ent = existing_fact.entity.strip().lower()
        norm_e_attr = existing_fact.attribute.strip().lower()
        norm_e_val = existing_fact.value.strip().lower()

        if norm_n_ent == norm_e_ent and norm_n_attr == norm_e_attr:
            return norm_n_val == norm_e_val
        else:
            return False

    # 3. Category mismatch check (e.g. profile vs event)
    if (
        hasattr(new_parsed, "category")
        and hasattr(existing_parsed, "category")
        and new_parsed.category != existing_parsed.category
    ):
        return False

    # 4. Strict Semantic Equivalence Signal when structured facts are unavailable
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


def classify_knowledge(
    parsed_memory,
    candidates,
):
    if not candidates:
        return KnowledgeDecision.NEW

    # 1. Scan candidates for strict fact UPDATE (same entity + same attribute + different value)
    if parsed_memory is not None:
        new_fact = extract_fact(parsed_memory)
        if new_fact is not None:
            norm_entity = new_fact.entity.strip().lower()
            norm_attribute = new_fact.attribute.strip().lower()
            norm_value = new_fact.value.strip().lower()

            for item in candidates:
                cand_mem = get_memory_object(item)
                if hasattr(cand_mem, "content"):
                    existing_parsed = parse_memory(cand_mem.content)
                    existing_fact = extract_fact(existing_parsed)
                    if existing_fact is not None:
                        ex_entity = existing_fact.entity.strip().lower()
                        ex_attribute = existing_fact.attribute.strip().lower()
                        ex_value = existing_fact.value.strip().lower()
                        if (
                            ex_entity == norm_entity
                            and ex_attribute == norm_attribute
                            and ex_value != norm_value
                        ):
                            return KnowledgeDecision.UPDATE

    # 2. Check for MERGE using explicit merge equivalence check
    if parsed_memory is not None:
        for item in candidates:
            cand_mem = get_memory_object(item)
            dist = (
                item[1]
                if hasattr(item, "__getitem__") and len(item) > 1
                else None
            )
            if is_merge_equivalent(parsed_memory, cand_mem, distance=dist):
                if (
                    hasattr(cand_mem, "content")
                    and parsed_memory.content.strip().lower()
                    == cand_mem.content.strip().lower()
                ):
                    return KnowledgeDecision.REINFORCEMENT
                return KnowledgeDecision.MERGE

    # 3. Distance classification against top candidate
    best_cand = candidates[0]
    best_mem = get_memory_object(best_cand)
    distance = (
        best_cand[1]
        if hasattr(best_cand, "__getitem__") and len(best_cand) > 1
        else None
    )

    if distance is None:
        return KnowledgeDecision.NEW

    if distance < 0.10:
        return KnowledgeDecision.REINFORCEMENT

    if distance < 0.35:
        return KnowledgeDecision.RELATED

    return KnowledgeDecision.NEW