from app.semantic.semantic_service import generate_embedding, semantic_search
from app.ranking_service import compute_hybrid_rank_score, STOP_WORDS
from app.graph.graph_service import GraphService
from app.graph.graph_search import GraphSearch
from app.context.query_entities import extract_query_entities
from app.models import Memory


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
        limit=20,
        query_embedding=query_emb,
    )

    for memory, distance in semantic_results:
        candidate_map[memory.id] = {
            "memory": memory,
            "semantic_distance": distance,
            "keyword_matched": False,
            "graph_connected": False,
        }

    # 2. Keyword Search
    words = [
        w.strip(".,!?\"'").lower()
        for w in query.split()
        if w.strip(".,!?\"'").lower() not in STOP_WORDS
        and len(w.strip(".,!?\"'")) > 1
    ]
    if not words:
        words = [
            w.strip(".,!?\"'").lower()
            for w in query.split()
            if len(w.strip(".,!?\"'")) > 1
        ]

    keyword_mids = set()
    if words:
        for word in words[:3]:
            q = db.query(Memory.id)
            if not include_archived:
                q = q.filter(Memory.state != "archived")
            kw_mems = (
                q.filter(Memory.content.ilike(f"%{word}%"))
                .limit(10)
                .all()
            )
            for row in kw_mems:
                mid = row[0]
                keyword_mids.add(mid)
                if mid in candidate_map:
                    candidate_map[mid]["keyword_matched"] = True

    # 3. Knowledge Graph Expansion (Robust entity & term matching)
    graph_service = GraphService()
    kg = graph_service.repository.load()
    graph_search = GraphSearch(nodes=kg.nodes, edges=kg.edges)

    query_entities = extract_query_entities(query)
    graph_terms = set()
    for entity in query_entities:
        ent_text = entity.text if hasattr(entity, "text") else str(entity)
        if ent_text and ent_text.strip():
            graph_terms.add(ent_text.strip().lower())

    # Include non-stopword query terms for robust graph candidate discovery
    for raw_term in query.split():
        clean_term = raw_term.strip(".,!?\"'").lower()
        if clean_term and clean_term not in STOP_WORDS and len(clean_term) > 1:
            graph_terms.add(clean_term)

    graph_mids = set()
    for term in graph_terms:
        matched = graph_search.memory_ids(term)
        graph_mids.update(matched)

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