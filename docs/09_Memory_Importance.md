# Memory Importance Scoring

The Memory Engine assigns an importance score when a memory is created.

Current rule-based scores:

- Profile → 0.95
- Preference → 0.80
- Habit → 0.70
- Event → 0.50
- Default → 0.40¸

This score will later be used for ranking, retrieval, and forgetting strategit

# Memory Retrieval

The Memory Engine retrieves memories ordered by importance.

Current strategy:

ORDER BY importance DESC

Future improvements:

- Recency
- Access Count
- Semantic Similarity
- Hybrid Ranking

# Memory Access Tracking

Each time a memory is retrieved:

- access_count is incremented.
- last_accessed is updated.

These metrics help determine which memories are actively used and support future ranking and forgetting strategies.

# Memory Search

The Memory Engine supports filtering by:

- Category
- Minimum importance
- Keyword

Multiple filters can be combined to retrieve only the most relevant memories.

Current keyword search uses SQL ILIKE for case-insensitive matching.

Future versions will replace keyword search with semantic vector search.