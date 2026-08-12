from app.database import SessionLocal
from app.agent_service import MemoryAgent


def test_agent_query_and_chat():
    db = SessionLocal()
    try:
        agent = MemoryAgent(db)
        chat_res = agent.chat("I love drinking espresso in Pune.", category="preference")
        assert "query" in chat_res
        assert "response" in chat_res
        assert "reflection" in chat_res

        query_res = agent.query("What drinks do I like?", top_k=3)
        assert query_res["query"] == "What drinks do I like?"
        assert isinstance(query_res["prompt"], str)
        assert len(query_res["prompt"]) > 0
    finally:
        db.close()
