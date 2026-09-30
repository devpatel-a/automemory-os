from app.understanding.models import ParsedMemory
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory
from app.knowledge.temporal_cues import has_transition_evidence
from app.knowledge.attribute_schema import is_single_valued


def detect_contradiction(
    new_memory: ParsedMemory,
    existing_memory,
) -> bool:
    """
    Generic fact domain contradiction detector.
    Returns True ONLY if incoming and existing facts share entity + attribute with differing values
    and represent conflicting current claims without historical transition context or transition phrasing.
    """
    if isinstance(existing_memory, (tuple, list)):
        existing_memory = existing_memory[0]

    if not hasattr(existing_memory, "content") and not isinstance(existing_memory, str):
        return False

    existing_content = (
        existing_memory if isinstance(existing_memory, str) else existing_memory.content
    )
    existing_parsed = parse_memory(existing_content)

    new_fact = extract_fact(new_memory)
    existing_fact = extract_fact(existing_parsed)

    if new_fact and existing_fact and new_fact.attribute and existing_fact.attribute:
        if (
            new_fact.entity.strip().lower() == existing_fact.entity.strip().lower()
            and new_fact.attribute.strip().lower() == existing_fact.attribute.strip().lower()
        ):
            # Same value is never a contradiction
            if new_fact.value.strip().lower() == existing_fact.value.strip().lower():
                return False

            # Multi-valued attributes: different values coexist ("I like coffee." + "I like tea.")
            if not is_single_valued(new_fact):
                return False

            # Explicit transition phrasing ("moved to", "transferred to", etc.) is NOT a contradiction
            content_lower = new_memory.content.lower()
            has_transition = has_transition_evidence(content_lower)
            if has_transition:
                return False

            # If incoming fact is FUTURE or HISTORICAL, it is not a current claim contradiction
            if new_fact.temporal_state in ("FUTURE", "HISTORICAL") or existing_fact.temporal_state in ("FUTURE", "HISTORICAL"):
                return False

            # Direct contradiction on current claims without transition evidence
            return True

    return False