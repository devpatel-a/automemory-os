from app.knowledge.fact_models import (
    KnowledgeFact,
)

from app.understanding.models import (
    ParsedMemory,
)


def extract_fact(
    memory: ParsedMemory,
) -> KnowledgeFact | None:

    text = memory.content.lower().strip()

    # Residence
    if "live in" in text:
        location = text.split("live in")[-1].strip(" .")
        return KnowledgeFact(
            entity="user",
            attribute="residence",
            value=location.lower().strip(),
        )
    elif "living in" in text:
        location = text.split("living in")[-1].strip(" .")
        return KnowledgeFact(
            entity="user",
            attribute="residence",
            value=location.lower().strip(),
        )

    # Favorite drink
    if "favorite drink is" in text:
        drink = text.split("favorite drink is")[-1].strip(" .")
        return KnowledgeFact(
            entity="user",
            attribute="favorite_drink",
            value=drink.lower().strip(),
        )

    # Workplace
    if "work at" in text:
        company = text.split("work at")[-1].strip(" .")
        return KnowledgeFact(
            entity="user",
            attribute="workplace",
            value=company.lower().strip(),
        )

    # Name
    if "my name is" in text:
        name = text.split("my name is")[-1].strip(" .")
        return KnowledgeFact(
            entity="user",
            attribute="name",
            value=name.lower().strip(),
        )

    return None