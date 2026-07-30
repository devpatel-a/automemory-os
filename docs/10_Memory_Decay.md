# Memory Decay

The Memory Engine evaluates memories during retrieval.

Current strategy:

If:

- importance < 0.5
- access_count < 3

Then:

- state = archived

Archived memories remain stored but are excluded from normal retrieval.

Future versions will use more advanced decay strategies based on age, recency, and semantic importance.