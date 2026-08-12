from app.knowledge.contradiction_detector import detect_contradiction
from app.understanding.memory_parser import parse_memory


def check_contradiction(
    new_memory,
    candidates,
):
    """
    Check if the incoming memory contradicts any existing candidate memory.
    Returns the contradicted Memory object if a contradiction is detected, else None.
    """
    if not candidates:
        return None

    if isinstance(new_memory, str):
        parsed = parse_memory(new_memory)
    elif hasattr(new_memory, "content"):
        parsed = parse_memory(new_memory.content)
    else:
        parsed = new_memory

    for item in candidates:
        memory = item[0] if isinstance(item, (tuple, list)) else item
        if detect_contradiction(parsed, memory):
            return memory

    return None