# Current Data Flow Reference

## Memory Processing Pipeline Flow (`MemoryPipeline.process`)

```
Natural Language User Input
      ↓
1. Understanding: parse_memory(content)
   • Extracts spaCy named entities & intent
   • Entity Resolution: user pronouns (I / me / my / myself → user entity) vs non-user entities (Rahul, brother → distinct entities)
  ↓
2. Candidate Discovery: semantic_search(db, content, limit=5)
   • Fetches top vector candidates for knowledge comparison
  ↓
3. Knowledge Reasoning: process_knowledge(parsed_memory, candidates)
   • Generic Fact Extraction (extract_fact):
     Extracts KnowledgeFact(entity, attribute, value, fact_type, temporal_info, confidence)
     using spaCy dependency parsing, POS tags, noun chunks, and centralized canonical attribute normalization
   • Zero Memory-Content Value Keywords:
     Does NOT use specific memory values (coffee, espresso, Pune, Google, Python, MacBook, iPhone, etc.)
   • Context-Aware Object Semantics:
     Uses POS and noun chunk head structure to conservatively classify DEVICE vs TOOL/OTHER
     ("I use a MacBook Air", "I use a computer", "I use a workstation" → device vs "I use Python for work", "I use Python", "I use a programming language" → tool)
   • Knowledge Classification (classify_knowledge):
     - UPDATE: same entity + same attribute + different value
     - MERGE: same entity + same attribute + same value
     - Unrelated attributes: must never UPDATE or MERGE
     - CONTRADICTION: same entity + same attribute + different value (archival lineage)
  ↓
4. Decision Mapping: decide(knowledge) → MemoryAction
  ↓
5. Memory Evolution Execution (app/service.py):
   • STORE         → create_memory()
   • REINFORCE     → reinforce_existing_memory()
   • UPDATE        → update_existing_fact_memory() (in-place fact update)
   • MERGE         → merge_existing_memories() (consolidates canonical, transfers relationships, archives redundant)
   • ARCHIVE       → contradict_existing_memory() (archives target with is_contradicted=True & contradicted_by_id)
   • RELATED       → create_memory() + create_relationship("related_to")
  ↓
6. Knowledge Graph Indexing: GraphService().process_memory(memory)
```

---

## Context Query Flow (`ContextEngine.build_context`)

```
Input Query String
  ↓
1. Query Understanding & Historical Detection:
   extract_query_entities(query) + is_historical_query(query)
  ↓
2. Candidate Retrieval:
   retrieve_memories(db, query, limit=10, include_archived=historical)
  ↓
3. Evidence Evaluation: evaluate_evidence(candidate, query, query_entities)
   • Calculates evidence_score combining base retrieval score, exact entity match,
     generic fact attribute match, category match, and temporal match
  ↓
4. Conflict Resolution & Lineage Safety: resolve_conflicts(candidates, query)
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
