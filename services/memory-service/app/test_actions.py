from app.intelligence.classifier import MemoryRelation
from app.intelligence.actions import execute_action


def test_actions_execution():
    for relation in MemoryRelation:
        action = execute_action(relation)
        assert action is not None
        assert hasattr(action, "value")