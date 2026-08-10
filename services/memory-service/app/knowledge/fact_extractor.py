from app.knowledge.fact_models import (
    KnowledgeFact,
)

from app.understanding.models import (
    ParsedMemory,
)


def extract_fact(
    memory: ParsedMemory,
) -> KnowledgeFact | None:

    text = memory.content.lower()

    # Residence
    if "live in" in text:

        location = text.split("live in")[-1].strip(" .")

        return KnowledgeFact(
            entity="user",
            attribute="residence",
            value=location,
        )

    # Favorite drink
    if "favorite drink is" in text:

        drink = (
            text.split("favorite drink is")[-1]
            .strip(" .")
        )

        return KnowledgeFact(
            entity="user",
            attribute="favorite_drink",
            value=drink,
        )

    return None