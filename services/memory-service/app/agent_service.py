from sqlalchemy.orm import Session

from app.context.context_engine import ContextEngine
from app.context.prompt_builder import build_prompt
from app.reflection_service import ReflectionEngine
from app.pipeline.memory_pipeline import MemoryPipeline
from app.retrieval_service import retrieve_memories


class MemoryAgent:
    """
    Agent Interface for AutoMemory OS.

    Integrates:
      Understanding -> Context Engine -> Prompt Builder -> Agent Generation -> Reflection Loop -> Memory Pipeline
    """

    def __init__(self, db: Session):
        self.db = db
        self.context_engine = ContextEngine()
        self.reflection_engine = ReflectionEngine()
        self.memory_pipeline = MemoryPipeline(db)

    def query(self, user_query: str, top_k: int = 5) -> dict:
        # 1. Build Context
        context_package = self.context_engine.build_context(
            db=self.db,
            query=user_query,
        )

        # 2. Build Prompt
        prompt = build_prompt(context_package)

        # 3. Retrieve raw memories used
        retrieved = retrieve_memories(
            db=self.db,
            query=user_query,
            limit=top_k,
        )
        memories_used = [m for m, _ in retrieved]

        # 4. Generate grounded agent response
        if memories_used:
            memory_summary = "; ".join([m.content for m in memories_used])
            response = f"Based on your stored memories ({memory_summary}), here is what I know regarding: '{user_query}'."
        else:
            response = f"I don't have any specific stored memories yet for '{user_query}'."

        # 5. Reflection Loop
        reflection_result = self.reflection_engine.reflect(
            db=self.db,
            query=user_query,
            response=response,
            memories_used=memories_used,
        )

        return {
            "query": user_query,
            "prompt": prompt,
            "response": response,
            "memories_used": memories_used,
            "reflection": reflection_result,
        }

    def chat(self, user_input: str, category: str = "fact") -> dict:
        # 1. Ingest input through Memory Pipeline
        pipeline_result = self.memory_pipeline.process(
            content=user_input,
            category=category,
        )

        # 2. Query Agent
        agent_result = self.query(user_query=user_input)
        agent_result["pipeline"] = pipeline_result
        return agent_result
