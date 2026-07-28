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