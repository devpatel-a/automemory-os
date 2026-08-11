from app.retrieval_service import (
    retrieve_memories,
)

from app.context.models import (
    ContextCandidate,
)

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

from app.context.ranker import (
    rank_candidates,
)

from app.context.diversity import (
    diversify_candidates,
)

from app.context.token_budget import (
    optimize_token_budget,
)

from app.context.assembler import (
    assemble_context,
)


class ContextEngine:
    """
    Main orchestration layer for
    intelligent context retrieval.
    """

    def build_context(
        self,
        db,
        query: str,
    ):

        # --------------------------
        # Understand Query
        # --------------------------

        query_entities = extract_query_entities(
            query,
        )

        # --------------------------
        # Semantic Retrieval
        # --------------------------

        results = retrieve_memories(
            db=db,
            query=query,
        )

        candidates = []

        # --------------------------
        # Initial Scoring
        # --------------------------

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

            score = (
                similarity
                + entity_bonus
                + category_bonus
                + temporal_bonus
            )

            candidates.append(

                ContextCandidate(

                    memory=memory,

                    similarity=similarity,

                    score=score,

                )

            )

        # --------------------------
        # Final Ranking
        # --------------------------

        ranked = rank_candidates(
            candidates,
        )

        # --------------------------
        # Diversity
        # --------------------------

        diversified = diversify_candidates(
            ranked,
            limit=10,
        )

        # --------------------------
        # Token Budget
        # --------------------------

        optimized = optimize_token_budget(
            diversified,
            max_characters=1200,
        )

        # --------------------------
        # Context Package
        # --------------------------

        return assemble_context(
            query=query,
            candidates=optimized,
        )