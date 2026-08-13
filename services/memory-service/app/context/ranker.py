from app.context.models import ContextCandidate


def rank_candidates(
    candidates: list[ContextCandidate],
) -> list[ContextCandidate]:
    """
    Rank candidates by their final evidence score descending.
    """
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.evidence_score
            if candidate.evidence_score > 0
            else candidate.score
        ),
        reverse=True,
    )