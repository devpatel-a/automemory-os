# Context Engine

The Context Engine is responsible for selecting the most relevant memories for the current user query.

It does not store memories.

It prepares the information that will later be sent to an LLM.

Initial strategy:

- Ignore archived memories
- Sort by importance
- Select the top K memories

Future versions will incorporate semantic similarity, recency, conversation state, confidence, and user feedback.