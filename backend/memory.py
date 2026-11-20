"""Bounded conversation history backed by SQLite."""
from backend import settings, storage


def create(owner_id: str = "local") -> str:
    return storage.create_conversation(owner_id)


def exists(cid: str) -> bool:
    return storage.conversation_exists(cid)


def claim(cid: str, owner_id: str = "local") -> bool:
    """Claim a legacy/client-created id, or verify its workspace owner."""
    current = storage.conversation_owner(cid)
    if current is None:
        storage.ensure_conversation(cid, owner_id)
        return storage.conversation_exists(cid, owner_id)
    if current == "local" and owner_id != "local":
        return storage.claim_legacy_workspace(cid, owner_id)
    return current == owner_id


def history(cid: str, owner_id: str | None = None) -> list[dict]:
    return storage.history(cid, owner_id)


def append(cid: str, role: str, content: str) -> None:
    storage.append_messages(cid, [(role, content)], settings.MEMORY_TURNS * 2)


def append_turn(cid: str, owner_id: str, question: str, answer: str, replace_reply: int | None = None) -> int | None:
    return storage.append_messages(cid, [("user", question), ("assistant", answer)],
                            settings.MEMORY_TURNS * 2, owner_id, replace_reply)


def last_assistant(cid: str, owner_id: str | None = None) -> str | None:
    for m in reversed(history(cid, owner_id)):
        if m["role"] == "assistant":
            return m["content"]
    return None


def delete(cid: str) -> bool:
    return storage.delete_conversation(cid)
