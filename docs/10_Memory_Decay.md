# Memory Decay

The Memory Engine evaluates memories during retrieval and reinforcement.

Current strategy (v0.9):

If:

- state = active
- importance < 0.5
- access_count < 3

Then:

- state = weak

Weak memories stay retrievable. Decay **never archives**. `archived` is reserved
for merged duplicates and contradicted memories (see `09_Memory_Lifecycle.md`).
Rarely accessed does not mean false, and old does not mean irrelevant.

> v0.8 archived such memories. Because decay also ran on reinforcement, a
> repeated low-importance fact (the API's default `fact` category) disappeared
> from retrieval.

Future versions will use more advanced decay strategies based on age, recency,
and semantic importance. Historical knowledge must never be deleted just
because it is old.
