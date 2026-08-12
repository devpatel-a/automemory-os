from app.context.context_models import ContextPackage


def build_prompt(
    context: ContextPackage,
) -> str:
    """
    Convert a ContextPackage into a complete structured prompt for an AI Agent.
    """

    sections = [
        "System: You are an intelligent AI assistant backed by AutoMemory OS.",
        "Use the relevant long-term memory context below to respond accurately to the user query.\n",
    ]

    sections.append(f"User Query:\n{context.query}\n")

    sections.append("Retrieved Long-Term Memories:")

    groups = [
        ("User Profile", context.profile),
        ("Preferences", context.preferences),
        ("Habits & Routines", context.habits),
        ("Past Events", context.events),
        ("General Facts", context.other),
    ]

    has_memories = False
    for title, memories in groups:
        if not memories:
            continue

        has_memories = True
        sections.append(f"\n[{title}]")
        for memory in memories:
            sections.append(f"- {memory}")

    if not has_memories:
        sections.append("- (No relevant prior memories found)")

    return "\n".join(sections).strip()