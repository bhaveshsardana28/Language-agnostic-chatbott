# 3-minute demo script — GAIA

Historical record of the earlier implementation. For current behavior, see the [project README](../README.md).


Practice against a fresh `New chat` (local history never leaks between runs).
Hotspot your laptop Wi-Fi so venue Wi-Fi can't break the demo. Rehearse the
Groq-free-tier warning: if you hit a rate limit mid-demo, say *"free tier —
one moment"* and continue; the UI already says it for you.

| # | Time | Action | What they see |
|---|---|---|---|
| 1 | 0:00 | Open **http://localhost:8000** (fresh chat) | Welcome: greeting cycling through 7 languages; six suggestion cards |
| 2 | 0:15 | Type EN: *"Explain machine learning in one sentence."* | Streamed reply, markdown, timestamp, actions row |
| 3 | 0:35 | Type HI: *"मशीन लर्निंग कैसे काम करती है?"* | Hindi reply + `हिन्दी · Hindi` chip + **Language switched: English → हिन्दी** divider |
| 4 | 0:55 | Type: *"Now answer in German: how does a neural network learn?"* | Language instruction honored — German reply, still same chat (memory!) |
| 5 | 1:15 | Type: *"मुझे new language सीखने में कितना time लगेगा?"* (mixed-script) | Debug ON → **Hindi primary, 2nd: English, code-switched, Deva+Latn** — the signature slide |
| 6 | 1:35 | Click **📄 Doc**, upload `demo/policy.pdf` (any English PDF; a .txt works) | Chip "Ready — N chunks"; ask in Spanish: *"¿Cuál es la política de reembolso?"* → Spanish answer grounded in the ENGLISH doc + **Sources: policy — chunk k** |
| 7 | 2:00 | Code: *"Write a Python binary search."* | Syntax-highlighted code block, language label, Copy button |
| 8 | 2:20 | Voice (Chrome): click mic, allow, speak *"अगला सवाल"* — or skip if venue audio is bad | Pulsing mic, transcript in composer (no auto-send), speech language in Settings |
| 9 | 2:35 | Hover a reply → **Listen** | Language-matched speech; honest refusal if no voice |
| 10 | 2:50 | Sidebar: export the chat → open the .md | History, rename/delete with confirm, local-storage privacy note |

**Talk track:** "One model, seven languages, zero per-language training — the
architecture is language-agnostic; the detector, router and retrieval are
measured at every stage, and the campus knowledge base from our graded FYP
lives on as one route of a general assistant."

**Failure drills:** LLM 429 → friendly retry message (wait 30 s); web tool
down → sources silently omitted, answer still streams; backend down →
offline banner + local history still browsable.
