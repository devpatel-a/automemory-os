# Current Data Flow Reference

## Memory Processing Pipeline Flow (`MemoryPipeline.process`)

```
Input Raw Text & Category
  ↓
1. Understanding: parse_memory(content) → ParsedMemory(entities, intent, temporal)
  ↓
2. Candidate Discovery: semantic_search(db, content, limit=5) → Top-5 Memory candidates
  ↓
3. Knowledge Reasoning: KnowledgeProcessor().process(parsed, candidates) → KnowledgeResult(decision, fact)
  ↓
4. Decision Mapping: DecisionEngine().evaluate(decision) → MemoryAction
  ↓
5. Memory Evolution Execution (app/service.py):
   • STORE         → create_memory(content, category, db)
   • REINFORCE     → reinforce_existing_memory(db, candidate)
   • UPDATE        → update_existing_fact_memory(db, candidate, new_content, category)
   • MERGE         → merge_existing_memories(db, candidates, new_content, category)
   • ARCHIVE       → contradict_existing_memory(db, target, new_memory_id) + create_memory()
   • RELATED       → create_memory(content, category, db) + create_relationship(source_id, target_id, "related_to")
  ↓
6. Knowledge Graph Indexing: GraphService().process_memory(memory)
```

---

## Context Query Flow (`ContextEngine.build_context`)

```
Input Query String
  ↓
1. Query Understanding & Historical Check:
   extract_query_entities(query) + is_historical_query(query)
  ↓
2. Candidate Retrieval:
   retrieve_memories(db, query, limit=10, include_archived=historical)
  ↓
3. Evidence Evaluation (evaluate_evidence):
   Calculates evidence_score = base_retrieval_score + entity_match_bonus
                             + fact_attribute_match_bonus + temporal_intent_bonus
  ↓
4. Conflict Resolution & Lineage Safety (resolve_conflicts):
   • Contradiction Lineage (contradicted_by_id)
   • Merge Safety (archived merged memories excluded if active canonical exists)
   • Fact Domain Resolution (created_at precedence for current queries)
  ↓
5. Context Re-ranking: rank_candidates(resolved) by evidence_score descending
  ↓
6. Diversity Optimization: diversify_candidates(ranked, limit=10) via Jaccard token overlap
  ↓
7. Token Budget Optimization: optimize_token_budget(diversified, max_characters=1200)
  ↓
8. Context Assembly: assemble_context(query, optimized) → ContextPackage
```
