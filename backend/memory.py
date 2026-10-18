"""Per-conversation bounded memory with a small durable SQLite backing store.

The deque remains a hot cache for the streaming path, while SQLite is the
source of truth across worker restarts. Only the last configured turns are
retained server-side; the browser can still keep its longer local history.
"""

from __future__ import annotations

from collections import deque

from backend import settings, storage

_conversations: dict[str, deque] = {}


def create(owner_id: str = "local") -> str:
    cid = storage.create_conversation(owner_id)
    _conversations[cid] = deque(maxlen=settings.MEMORY_TURNS * 2)
    return cid


def exists(cid: str) -> bool:
    return cid in _conversations or storage.conversation_exists(cid)


def claim(cid: str, owner_id: str = "local") -> bool:
    """Claim a legacy/client-created id, or verify its workspace owner."""
    current = storage.conversation_owner(cid)
    if current is None:
        storage.ensure_conversation(cid, owner_id)
        return True
    if current == "local" and owner_id != "local":
        return storage.claim_legacy_workspace(cid, owner_id)
    return current == owner_id


def history(cid: str) -> list[dict]:
    dq = _conversations.get(cid)
    if dq is not None:
        return list(dq)
    loaded = storage.history(cid)
    if loaded:
        _conversations[cid] = deque(loaded, maxlen=settings.MEMORY_TURNS * 2)
    return loaded


def append(cid: str, role: str, content: str) -> None:
    if not exists(cid):
        return
    _conversations.setdefault(cid, deque(history(cid), maxlen=settings.MEMORY_TURNS * 2))
    _conversations[cid].append({"role": role, "content": content})
    storage.append_message(cid, role, content, settings.MEMORY_TURNS * 2)


def last_assistant(cid: str) -> str | None:
    for m in reversed(history(cid)):
        if m["role"] == "assistant":
            return m["content"]
    return None


def delete(cid: str) -> bool:
    cached = _conversations.pop(cid, None) is not None
    return storage.delete_conversation(cid) or cached
