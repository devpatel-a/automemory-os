# Memory Orchestrator

The Memory Orchestrator coordinates the memory ingestion workflow.

Responsibilities:

- Generate embeddings
- Retrieve semantic candidates
- Detect duplicates
- Construct memory objects

The orchestrator does not persist data.

Persistence remains the responsibility of the service layer.