from app.retrieval_service import retrieve_memories

from app.context.models import ContextCandidate
from app.context.ranker import rank_candidates


class ContextEngine:

    def build_context(
        self,
        db,
        query: str,
    ):
        # Retrieve memories
        results = retrieve_memories(
            db,
            query,
        )

        candidates = []

        # Convert retrieval results into ContextCandidate objects
        for memory, similarity in results:

            candidates.append(
                ContextCandidate(
                    memory=memory,
                    similarity=similarity,
                )
            )

        # Rank candidates
        ranked = rank_candidates(candidates)

        from app.context.assembler import (
            assemble_context,
        )

        ...

        context = assemble_context(
            query,
            ranked,
        )

        from app.context.prompt_builder import (
            build_prompt,
        )

        ...

        context = assemble_context(
            query,
            ranked,
        )

        prompt = build_prompt(
            context,
        )

        return prompt