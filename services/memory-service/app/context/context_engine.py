from app.retrieval_service import retrieve_memories

from app.context.models import ContextCandidate
from app.context.ranker import rank_candidates
from app.context.assembler import assemble_context
from app.context.query_entities import extract_query_entities
from app.context.entity_matcher import entity_match_score
from app.context.category_matcher import category_match_score


class ContextEngine:
    """
    Coordinates context construction.
    """

    def build_context(
        self,
        db,
        query: str,
    ):

        # ---------------------------------
        # Understand Query
        # ---------------------------------

        query_entities = extract_query_entities(
            query,
        )

        print("\n===== Query Entities =====")

        for entity in query_entities:
            print(entity)

        print("==========================\n")

        # ---------------------------------
        # Semantic Retrieval
        # ---------------------------------

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

            initial_score = (
                similarity
                + entity_bonus
                + category_bonus
            )

            print("--------------------------------")
            print(memory.content)
            print("Similarity :", similarity)
            print("Entity Bonus :", entity_bonus)
            print("Category Bonus :", category_bonus)
            print("Initial Score :", initial_score)

            candidates.append(

                ContextCandidate(

                    memory=memory,

                    similarity=similarity,

                    score=initial_score,

                )

            )

        # ---------------------------------
        # Rank Candidates
        # ---------------------------------

        ranked = rank_candidates(
            candidates,
        )

        # ---------------------------------
        # Assemble Context
        # ---------------------------------

        context = assemble_context(
            query,
            ranked,
        )

        return context