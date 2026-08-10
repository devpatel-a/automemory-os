# Confidence Engine

The Confidence Engine tracks how strongly AutoMemory OS believes a knowledge fact.

Each fact contains:

- confidence
- evidence_count
- contradiction_count

Confidence increases when new evidence reinforces the fact and decreases when contradictory evidence appears.

Future versions may incorporate time decay, source reliability, and learned confidence models.