from .models import Memory

memories = []


def get_memories():
    return memories


def add_memory(memory: Memory):
    memories.append(memory.model_dump())

    return {
        "message": "Memory added successfully.",
        "memory": memory
    }


def update_memory(memory_id: int, memory: Memory):
    if memory_id >= len(memories):
        return {
            "error": "Memory not found."
        }

    memories[memory_id] = memory.model_dump()

    return {
        "message": "Memory updated successfully.",
        "memory": memories[memory_id]
    }


def delete_memory(memory_id: int):
    if memory_id >= len(memories):
        return {
            "error": "Memory not found."
        }

    deleted = memories.pop(memory_id)

    return {
        "message": "Memory deleted successfully.",
        "deleted": deleted
    }