# Context Service

The Context Service is responsible for selecting memories that will be used by the AI.

Responsibilities:

- Read memories
- Filter archived memories
- Rank by importance
- Return the top K memories

The Context Service does not:

- Create memories
- Update memories
- Delete memories

Future versions will support:

- Semantic search
- Conversation awareness
- Token budgeting
- Context compression
- Prompt construction