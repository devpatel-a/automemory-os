from app.context.context_models import (
    ContextPackage,
)


def assemble_context(
    query: str,
    candidates,
):

    context = ContextPackage(
        query=query,
    )

    for candidate in candidates:

        memory = candidate.memory

        if memory.category == "profile":
            context.profile.append(
                memory.content
            )

        elif memory.category == "preference":
            context.preferences.append(
                memory.content
            )

        elif memory.category == "habit":
            context.habits.append(
                memory.content
            )

        elif memory.category == "event":
            context.events.append(
                memory.content
            )

        else:
            context.other.append(
                memory.content
            )

    return context