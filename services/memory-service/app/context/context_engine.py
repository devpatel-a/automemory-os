from app.config import settings
from app.retrieval_service import retrieve_candidates
from app.context.models import ContextCandidate
from app.context.query_entities import extract_query_entities
from app.context.evidence_evaluator import evaluate_evidence
from app.context.conflict_resolver import resolve_conflicts
from app.context.query_intent import HISTORICAL, analyze_query
from app.lineage import historical_memory_ids
from app.context.ranker import rank_candidates
from app.context.diversity import diversify_candidates
from app.context.token_budget import optimize_token_budget
from app.context.assembler import assemble_context

# Explicit bonus for candidates whose effective temporal state matches the
# query's temporal intent (e.g. HISTORICAL facts for "Where did I live before?").
# Measured by app/evaluation (temporal benchmark scenarios).
TEMPORAL_ALIGNMENT_BONUS = 0.25


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
        limit: int | None = None,
    ):
        """
        Build the final ContextPackage. `limit` caps how many memories are
        selected (defaults to CONTEXT_RETRIEVAL_LIMIT). The package's
        evidence is the single source of truth for what a downstream
        prompt/agent may use.
        """
        selection_limit = min(limit, settings.context_retrieval_limit) if limit else settings.context_retrieval_limit
        if not query or not query.strip():
            return assemble_context(query=query, candidates=[])

        # 1. Query Understanding: entities + structural intent (entity, attribute, temporal intent)
        query_entities = extract_query_entities(query)
        intent = analyze_query(query)
        historical = intent.temporal_intent == HISTORICAL

        # 2. Hybrid Candidate Retrieval (passes include_archived=historical)
        results = retrieve_candidates(
            db=db,
            query=query,
            limit=settings.context_retrieval_limit,
            include_archived=historical,
        )

        if not results:
            return assemble_context(query=query, candidates=[], intent=intent)

        # 3. Candidate Pool & Initial Wrapping (similarity = hybrid retrieval
        #    score, kept for backward compatibility; see .retrieval for signals)
        raw_candidates = [
            ContextCandidate(
                memory=rc.memory,
                similarity=rc.retrieval_score,
                retrieval=rc,
                explanation=[f"retrieval: {', '.join(rc.reasons) or 'ranked'}"],
            )
            for rc in results
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
            superseded_ids=historical_memory_ids(db, [c.memory.id for c in evaluated_candidates]),
        )

        # 5b. Temporal intent alignment
        for c in resolved_candidates:
            if is_completed_plan(c):
                # A fulfilled plan is history *as a plan*: it never answers a
                # future question, but its value was never a past state either.
                c.explanation.append("temporal_alignment: skipped (fulfilled plan)")
            elif c.temporal_state and c.temporal_state == intent.temporal_intent:
                c.evidence_score += TEMPORAL_ALIGNMENT_BONUS
                c.score = c.evidence_score
                c.explanation.append(
                    f"temporal_alignment ({intent.temporal_intent}): +{TEMPORAL_ALIGNMENT_BONUS:.3f}"
                )
                if c.retrieval is not None:
                    c.retrieval.temporal_score = (c.retrieval.temporal_score or 0.0) + TEMPORAL_ALIGNMENT_BONUS
            if c.retrieval is not None:
                c.retrieval.temporal_state = c.temporal_state
                c.retrieval.final_score = c.evidence_score

        # 6. Context Re-ranking
        ranked = rank_candidates(resolved_candidates)

        # 7. Near-Duplicate Diversity Optimization
        diversified = diversify_candidates(
            ranked,
            limit=selection_limit,
        )

        # 8. Token Budget Optimization
        optimized = optimize_token_budget(
            diversified,
            max_characters=settings.context_token_budget,
        )

        # 9. Context Assembly
        return assemble_context(
            query=query,
            candidates=optimized,
            intent=intent,
        )


def is_completed_plan(candidate) -> bool:
    """A stored FUTURE fact whose effective state became HISTORICAL through lineage."""
    return (
        candidate.fact is not None
        and candidate.fact.temporal_state == "FUTURE"
        and candidate.temporal_state == "HISTORICAL"
    )


def load_superseded_ids(db, memory_ids: list[int]) -> set[int]:
    """Backward-compatible alias: ids with historical lineage (superseded/fulfilled)."""
    return historical_memory_ids(db, memory_ids)
