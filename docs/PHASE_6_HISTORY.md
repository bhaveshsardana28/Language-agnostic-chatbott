# Phase 6 — Local conversation history

**Implemented 13 October 2026.** The default entry point is
`http://localhost:8000/`; the direct V2 asset path remains
`/static/v2/index.html`.

## Delivered

- Completed V2 conversations are stored in the V2-only `gaia.history.v2` record.
  The legacy `gaia.store.v1` storage is never read or modified.
- Stored records contain an ID, title, timestamps, server conversation ID and
  serializable user/assistant messages. DOM nodes, abort controllers and other
  runtime references are excluded.
- Titles are generated from the first user message and capped at 80 characters.
- Reload restores the active conversation, message content, language metadata,
  route metadata, timestamps, script labels, Insights data and server ID.
- The sidebar now lists conversations by most recently updated, with message count
  and date. Selecting a row restores it without duplicating turns.
- New chat clears the active view but preserves saved conversations; the next send
  creates a new local record.
- Sidebar search filters title and message content, shows highlighted matches and an
  explicit no-results state. Conversation rows expose separate labeled Rename,
  Export and Delete controls.
- Saved conversations are grouped by recency under Today, Yesterday, Previous 7
  days and Older headings while retaining descending `updatedAt` order.
- Rename validates and trims an 80-character title, updates the active header and
  persists it. Export downloads a sanitized Markdown transcript with roles,
  timestamps and language markers.
- Delete uses an accessible confirmation. It removes the local record, restores the
  most recent remaining conversation when needed, and attempts server cleanup using
  the server-issued ID. A server cleanup failure is surfaced as a partial-failure
  toast rather than hidden.
- Malformed history falls back to an empty history. Storage/quota failures keep the
  current tab usable and show a non-blocking notice.
- The composer now states the Phase 6 browser-history behavior. The backend memory
  boundary remains honest: a server restart can remove conversational context even
  when the browser still has the rendered local history.

## Implementation

| File | Responsibility |
|---|---|
| `static/v2/js/history.js` | V2 storage key, validation, serialization, loading and record helpers |
| `static/v2/js/chat.js` | Active-record lifecycle, persistence, restore, sidebar search/actions and New chat behavior |
| `static/v2/js/api.js` | Existing server conversation deletion boundary |
| `static/v2/js/shell.js` | Existing shell/new-chat controls remain the entry points |
| `static/v2/index.html` | Real history list and browser-history copy |
| `static/v2/css/shell.css` | Accessible, responsive conversation rows |
| `scripts/verify_history.py` | Persistence, reload, switching, malformed and blocked-storage browser checks |

## Verification

```text
./venv/bin/python scripts/verify_history.py --capture
10 Phase 6 check groups passed; 1 screenshot.

make test
core, V2, and code-switching tests passed

node --check static/v2/js/chat.js
node --check static/v2/js/history.js
node --check static/v2/js/main.js

git diff --check
clean
```

Evidence is recorded in `docs/history-checks.json` and
`docs/screenshots/phase6/light-1440-history.png`.

## Remaining Phase 6 work

Delete-all-data, documents/upload/list/clear, and source cards remain separate
follow-up slices. The local conversation lifecycle and per-conversation controls
are now in place for those features to reuse.
