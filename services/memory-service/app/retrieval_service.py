from app.semantic.semantic_service import semantic_search
from app.ranking_service import calculate_score
from app.graph.graph_service import GraphService
from app.graph.graph_search import GraphSearch
from app.context.query_entities import extract_query_entities
from app.models import Memory


def retrieve_memories(
    db,
    query: str,
    limit: int = 5,
):
    """
    Central Hybrid Retrieval API.

    Sources:
        • Semantic Vector Search (pgvector)
        • Keyword Text Search
        • Knowledge Graph Node Traversal & Expansion
    """

    candidates = {}

    # 1. Semantic Search
    semantic_results = semantic_search(
        db=db,
        query=query,
        limit=20,
    )

    for memory, distance in semantic_results:
        if memory.state == "archived":
            continue
        dist_val = distance if distance is not None else 0.5
        base_score = calculate_score(memory, dist_val)
        candidates[memory.id] = {
            "memory": memory,
            "semantic_score": base_score,
            "keyword_bonus": 0.0,
            "graph_bonus": 0.0,
        }

    # 2. Keyword Search
    words = [w.strip() for w in query.lower().split() if len(w.strip()) > 3]
    if words:
        keyword_memories = (
            db.query(Memory)
            .filter(Memory.state != "archived")
            .filter(Memory.content.ilike(f"%{words[0]}%"))
            .limit(10)
            .all()
        )
        for memory in keyword_memories:
            if memory.id in candidates:
                candidates[memory.id]["keyword_bonus"] += 0.15
            else:
                candidates[memory.id] = {
                    "memory": memory,
                    "semantic_score": calculate_score(memory, 0.4),
                    "keyword_bonus": 0.20,
                    "graph_bonus": 0.0,
                }

    # 3. Knowledge Graph Expansion
    try:
        graph_service = GraphService()
        kg = graph_service.repository.load()
        graph_search = GraphSearch(nodes=kg.nodes, edges=kg.edges)

        query_entities = extract_query_entities(query)
        matched_mids = set()
        for entity in query_entities:
            matched_mids.update(graph_search.memory_ids(entity))

        if matched_mids:
            graph_memories = (
                db.query(Memory)
                .filter(Memory.id.in_(matched_mids), Memory.state != "archived")
                .all()
            )
            for memory in graph_memories:
                if memory.id in candidates:
                    candidates[memory.id]["graph_bonus"] += 0.25
                else:
                    candidates[memory.id] = {
                        "memory": memory,
                        "semantic_score": calculate_score(memory, 0.3),
                        "keyword_bonus": 0.0,
                        "graph_bonus": 0.25,
                    }
    except Exception:
        pass

    # Calculate final hybrid score
    ranked = []
    for item in candidates.values():
        total_score = (
            item["semantic_score"]
            + item["keyword_bonus"]
            + item["graph_bonus"]
        )
        ranked.append((item["memory"], total_score))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[:limit]