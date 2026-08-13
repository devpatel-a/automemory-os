from app.understanding.models import ParsedMemory
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory


def detect_contradiction(
    new_memory: ParsedMemory,
    existing_memory,
) -> bool:
    """
    Generic fact domain contradiction detector.
    Returns True ONLY if incoming and existing facts share entity + attribute with differing values.
    Unrelated attributes never contradict.
    """
    if isinstance(existing_memory, (tuple, list)):
        existing_memory = existing_memory[0]

    if not hasattr(existing_memory, "content") and not isinstance(existing_memory, str):
        return False

    existing_parsed = (
        parse_memory(existing_memory)
        if isinstance(existing_memory, str)
        else parse_memory(existing_memory.content)
    )

    new_fact = extract_fact(new_memory)
    existing_fact = extract_fact(existing_parsed)

    if new_fact and existing_fact and new_fact.attribute and existing_fact.attribute:
        if (
            new_fact.entity.strip().lower() == existing_fact.entity.strip().lower()
            and new_fact.attribute.strip().lower() == existing_fact.attribute.strip().lower()
        ):
            return new_fact.value.strip().lower() != existing_fact.value.strip().lower()

    return False