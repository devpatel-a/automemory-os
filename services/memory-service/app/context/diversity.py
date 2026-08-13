from app.context.models import ContextCandidate
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory

STOP_WORDS = {
    "the", "is", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "my", "i", "me", "do", "you", "what", "where", "how"
}


def get_token_set(text: str) -> set[str]:
    words = [
        w.strip(".,!?\"'").lower()
        for w in text.split()
        if w.strip(".,!?\"'").lower() not in STOP_WORDS
        and len(w.strip(".,!?\"'")) > 1
    ]
    if not words:
        words = [
            w.strip(".,!?\"'").lower()
            for w in text.split()
            if len(w.strip(".,!?\"'")) > 1
        ]
    return set(words)


def calculate_token_overlap(t1: set[str], t2: set[str]) -> float:
    if not t1 or not t2:
        return 0.0
    return len(t1.intersection(t2)) / float(len(t1.union(t2)))


def diversify_candidates(
    candidates: list[ContextCandidate],
    limit: int = 5,
) -> list[ContextCandidate]:
    """
    Remove exact and near-duplicate memories using Jaccard token overlap.
    Differentiates distinct fact value transitions (e.g. Pune vs Mumbai) from true paraphrases.
    """
    selected = []
    seen_contents = []
    seen_facts = []  # list of (content, token_set, KnowledgeFact)

    for candidate in candidates:
        content = candidate.memory.content.strip().lower()

        # 1. Exact text duplicate check
        if content in seen_contents:
            candidate.explanation.append("diversity: excluded (exact duplicate)")
            continue

        parsed = parse_memory(candidate.memory.content)
        fact = extract_fact(parsed)
        tokens = get_token_set(content)
        is_near_dup = False

        for prev_content, prev_tokens, prev_fact in seen_facts:
            # If structured facts exist with same entity & attribute but different values,
            # they are distinct facts (e.g., Pune vs Mumbai) and not near-duplicate paraphrases.
            if (
                fact and prev_fact
                and fact.entity and prev_fact.entity
                and fact.attribute and prev_fact.attribute
                and fact.entity.lower() == prev_fact.entity.lower()
                and fact.attribute.lower() == prev_fact.attribute.lower()
                and fact.value.lower() != prev_fact.value.lower()
            ):
                continue

            overlap = calculate_token_overlap(tokens, prev_tokens)
            if overlap >= 0.20:
                is_near_dup = True
                candidate.explanation.append(
                    f"diversity: excluded (near-duplicate overlap={overlap:.2f})"
                )
                break

        if is_near_dup:
            continue

        seen_contents.append(content)
        seen_facts.append((content, tokens, fact))
        selected.append(candidate)

        if len(selected) >= limit:
            break

    return selected