from app.knowledge.fact_models import (
    KnowledgeFact,
)

from app.knowledge.confidence_engine import (
    reinforce_fact,
    contradict_fact,
)

fact = KnowledgeFact(

    entity="user",

    attribute="favorite_drink",

    value="coffee",

)

print(fact)

print()

reinforce_fact(fact)

reinforce_fact(fact)

print(fact)

print()

contradict_fact(fact)

print(fact)