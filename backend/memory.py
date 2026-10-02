"""Per-conversation bounded memory. In-process by design: no auth, no
long-term persistence (server restart = gone), last N turns only.
Client owns durable history in localStorage (FYP UI already does that)."""

from __future__ import annotations

import uuid
from collections import deque

from backend import settings

_conversations: dict[str, deque] = {}


def create() -> str:
    cid = uuid.uuid4().hex[:12]
    _conversations[cid] = deque(maxlen=settings.MEMORY_TURNS * 2)
    return cid


def exists(cid: str) -> bool:
    return cid in _conversations


def history(cid: str) -> list[dict]:
    dq = _conversations.get(cid)
    return list(dq) if dq is not None else []


def append(cid: str, role: str, content: str) -> None:
    if cid in _conversations:
        _conversations[cid].append({"role": role, "content": content})


def last_assistant(cid: str) -> str | None:
    for m in reversed(history(cid)):
        if m["role"] == "assistant":
            return m["content"]
    return None


def delete(cid: str) -> bool:
    return _conversations.pop(cid, None) is not None
