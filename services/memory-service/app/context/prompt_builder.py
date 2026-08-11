from app.context.context_models import (
    ContextPackage,
)


def build_prompt(
    context: ContextPackage,
) -> str:
    """
    Convert a ContextPackage into a
    prompt for the LLM.
    """

    sections = []

    sections.append(
        f"User Query:\n{context.query}\n"
    )

    groups = [
        ("Profile", context.profile),
        ("Preferences", context.preferences),
        ("Habits", context.habits),
        ("Events", context.events),
        ("Other", context.other),
    ]

    for title, memories in groups:

        if not memories:
            continue

        sections.append(f"{title}:")

        for memory in memories:

            sections.append(
                f"- {memory}"
            )

        sections.append("")

    return "\n".join(sections).strip()