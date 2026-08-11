from app.retrieval_service import retrieve_memories

from app.context.models import ContextCandidate

from app.context.ranker import rank_candidates

from app.context.assembler import assemble_context

from app.context.query_entities import (
    extract_query_entities,
)

from app.context.entity_matcher import (
    entity_match_score,
)

from app.context.category_matcher import (
    category_match_score,
)

from app.context.temporal_matcher import (
    temporal_match_score,
)

from app.context.diversity import (
    diversify_candidates,
)


class ContextEngine:

    def build_context(
        self,
        db,
        query: str,
    ):

        query_entities = extract_query_entities(
            query,
        )

        print("\n===== Query Entities =====")

        for entity in query_entities:
            print(entity)

        print("==========================\n")

        results = retrieve_memories(
            db,
            query,
        )

        candidates = []

        for memory, similarity in results:

            entity_bonus = entity_match_score(
                query_entities,
                memory.content,
            )

            category_bonus = category_match_score(
                query,
                memory.category,
            )

            temporal_bonus = temporal_match_score(
                query,
                memory.content,
            )

            initial_score = (
                similarity
                + entity_bonus
                + category_bonus
                + temporal_bonus
            )

            candidates.append(

                ContextCandidate(

                    memory=memory,

                    similarity=similarity,

                    score=initial_score,

                )

            )

        ranked = rank_candidates(
            candidates,
        )

        diversified = diversify_candidates(
            ranked,
            limit=5,
        )

        context = assemble_context(
            query,
            diversified,
        )

        return context