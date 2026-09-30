from app.semantic.semantic_service import generate_embedding, semantic_search
from app.ranking_service import compute_hybrid_rank_score
from app.lexical import fts_match_any, query_terms
from app.graph.sql_repository import SqlGraphRepository
from app.models import Memory

# Bounded candidate pools per retrieval signal
SEMANTIC_CANDIDATE_LIMIT = 20
LEXICAL_CANDIDATE_LIMIT = 30


def retrieve_memories(
    db,
    query: str,
    limit: int = 5,
    include_archived: bool = False,
):
    """
    Central Hybrid Retrieval API with Candidate Fusion & Multi-Signal Feature Ranking.

    Flow:
        Query → Semantic Retrieval → Keyword Retrieval → Graph Retrieval
        → Candidate Deduplication → Feature Scoring → Final Ranking → Filtering → Top N Memories
    """
    if not query or not query.strip():
        return []

    # Performance: Generate query embedding ONCE and reuse it for semantic search
    query_emb = generate_embedding(query)

    # Dictionary to deduplicate candidate memories by memory_id
    candidate_map = {}

    # 1. Semantic Search (reusing query_emb)
    semantic_results = semantic_search(
        db=db,
        query=query,
        limit=SEMANTIC_CANDIDATE_LIMIT,
        query_embedding=query_emb,
        include_archived=include_archived,
    )

    for memory, distance in semantic_results:
        candidate_map[memory.id] = {
            "memory": memory,
            "semantic_distance": distance,
            "keyword_matched": False,
            "graph_connected": False,
        }

    # 2. Lexical Search (PostgreSQL full-text search on whole words:
    #    "car" matches "cars", never "career" / "scary" / "carpool")
    terms = query_terms(query)
    keyword_mids = set()
    if terms:
        q = db.query(Memory.id).filter(fts_match_any(Memory.content, terms))
        if not include_archived:
            q = q.filter(Memory.state != "archived")
        for (mid,) in q.limit(LEXICAL_CANDIDATE_LIMIT).all():
            keyword_mids.add(mid)
            if mid in candidate_map:
                candidate_map[mid]["keyword_matched"] = True

    # 3. Knowledge Graph Expansion (persistent graph, conservative entity resolution:
    #    exact normalized names / explicit aliases, longest span first)
    graph_mids = SqlGraphRepository(db).memory_ids_for_query(query)

    for mid in graph_mids:
        if mid in candidate_map:
            candidate_map[mid]["graph_connected"] = True

    # 4. Bulk Fetch missing Memory objects in a SINGLE database query to avoid N+1 issues
    all_needed_mids = (keyword_mids | graph_mids) - set(candidate_map.keys())
    if all_needed_mids:
        q_missing = db.query(Memory).filter(Memory.id.in_(all_needed_mids))
        if not include_archived:
            q_missing = q_missing.filter(Memory.state != "archived")
        missing_memories = q_missing.all()

        for memory in missing_memories:
            candidate_map[memory.id] = {
                "memory": memory,
                "semantic_distance": None,
                "keyword_matched": memory.id in keyword_mids,
                "graph_connected": memory.id in graph_mids,
            }

    # 5. Feature Scoring & Filtering
    ranked = []
    for item in candidate_map.values():
        memory = item["memory"]

        # If not include_archived, archived memories are strictly excluded
        if not include_archived and getattr(memory, "state", None) == "archived":
            continue

        score = compute_hybrid_rank_score(
            memory=memory,
            semantic_distance=item["semantic_distance"],
            keyword_matched=item["keyword_matched"],
            graph_connected=item["graph_connected"],
            query=query,
        )

        ranked.append((memory, score))

    # 6. Final Ranking
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:limit]