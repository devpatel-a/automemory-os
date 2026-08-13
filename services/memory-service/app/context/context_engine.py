from app.retrieval_service import retrieve_memories
from app.context.models import ContextCandidate
from app.context.query_entities import extract_query_entities
from app.context.evidence_evaluator import evaluate_evidence
from app.context.conflict_resolver import resolve_conflicts, is_historical_query
from app.context.ranker import rank_candidates
from app.context.diversity import diversify_candidates
from app.context.token_budget import optimize_token_budget
from app.context.assembler import assemble_context


class ContextEngine:
    """
    Main orchestration layer for intelligent evidence selection and context quality.

    Flow:
        Query → Query Understanding → Historical Check → Hybrid Candidate Retrieval
        → Candidate Pool → Evidence Evaluation → Conflict Resolution → Context Re-ranking
        → Diversity → Token Budget → Context Assembly
    """

    def build_context(
        self,
        db,
        query: str,
    ):
        if not query or not query.strip():
            return assemble_context(query=query, candidates=[])

        # 1. Query Understanding & Historical Query Check
        query_entities = extract_query_entities(query)
        historical = is_historical_query(query)

        # 2. Hybrid Candidate Retrieval (passes include_archived=historical)
        results = retrieve_memories(
            db=db,
            query=query,
            limit=10,
            include_archived=historical,
        )

        if not results:
            return assemble_context(query=query, candidates=[])

        # 3. Candidate Pool & Initial Wrapping
        raw_candidates = [
            ContextCandidate(
                memory=memory,
                similarity=similarity,
            )
            for memory, similarity in results
        ]

        # 4. Evidence Evaluation (Zero hardcoded domain rules)
        evaluated_candidates = [
            evaluate_evidence(
                candidate=c,
                query=query,
                query_entities=query_entities,
            )
            for c in raw_candidates
        ]

        # 5. Conflict Resolution & Contradiction/Merge Safety
        resolved_candidates = resolve_conflicts(
            candidates=evaluated_candidates,
            query=query,
        )

        # 6. Context Re-ranking
        ranked = rank_candidates(resolved_candidates)

        # 7. Near-Duplicate Diversity Optimization
        diversified = diversify_candidates(
            ranked,
            limit=10,
        )

        # 8. Token Budget Optimization
        optimized = optimize_token_budget(
            diversified,
            max_characters=1200,
        )

        # 9. Context Assembly
        return assemble_context(
            query=query,
            candidates=optimized,
        )