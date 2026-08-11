from app.context.context_models import (
    ContextPackage,
)


def build_prompt(
    context: ContextPackage,
) -> str:

    prompt = []

    prompt.append(
        "Relevant User Context\n"
    )

    if context.profile:

        prompt.append(
            "\nProfile\n-------"
        )

        for item in context.profile:
            prompt.append(
                f"- {item}"
            )

    if context.preferences:

        prompt.append(
            "\nPreferences\n-----------"
        )

        for item in context.preferences:
            prompt.append(
                f"- {item}"
            )

    if context.habits:

        prompt.append(
            "\nHabits\n------"
        )

        for item in context.habits:
            prompt.append(
                f"- {item}"
            )

    if context.events:

        prompt.append(
            "\nEvents\n------"
        )

        for item in context.events:
            prompt.append(
                f"- {item}"
            )

    prompt.append(
        "\nUser Query\n----------"
    )

    prompt.append(
        context.query
    )

    return "\n".join(prompt)