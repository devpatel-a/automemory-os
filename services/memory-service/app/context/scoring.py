from app.context.models import ContextCandidate
from app.context.evidence_evaluator import evaluate_evidence


def calculate_context_score(
    candidate: ContextCandidate,
    query: str = "",
    query_entities: list | None = None,
) -> float:
    """
    Unified entry point for Context Evidence Scoring.
    Delegates to evaluate_evidence to enforce one authoritative scoring path.
    """
    evaluated = evaluate_evidence(
        candidate=candidate,
        query=query,
        query_entities=query_entities or [],
    )
    return evaluated.evidence_score