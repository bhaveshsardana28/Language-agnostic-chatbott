# Stability Report — Phase 1 (all results from real runs, 30 Sep 2026)

Suite: `tests/test_browser.py` — **28/28 PASS** (Playwright/Chromium against
the live server). Companion suites also green: 10 FYP · 11 v2-API ·
26 code-switching detection.

## Bugs: root cause → fix → verified result

### BUG 1 — Scrolling broken (reported by user)
- **ROOT CAUSE** (4 interacting, in `templates/index.html`):
  1. `min-height:auto` on grid/flex items (`.main`, `#chat`) lets content
     size blow past `100dvh` — Safari-fragile; no element owns scrolling.
  2. Delta handler force-set `scrollTop = scrollHeight` on EVERY streamed
     token → user cannot scroll up during generation (the exact complaint).
  3. `paintMsg` force-scrolled per message → 120-message restore = 120
     queued `scroll-behavior:smooth` animations = jitter.
  4. `height:100dvh` with no `100vh` fallback.
- **FIX**: structural `min-height:0` chain + `height:100vh;height:100dvh`
  fallback; scroll engine (`isNearBottom(120px)` gate, rAF-throttled
  `scheduleFollow`, explicit `scrollBottom`); jump pill "New messages";
  one batched scroll on conversation open; smooth-scroll removed.
- **TEST → RESULT (PASS)**: 120-message conversation owns scroll; scroll-up
  works; pill appears when scrolled up; pill returns to bottom;
  `scheduleFollow()` does NOT move a scrolled-up viewport (anti-force) and
  resumes following near bottom; composer stays in viewport at scroll top.

### BUG 2 — XSS: escaper was identity (mangled entity map)
- **ROOT CAUSE**: `esc()` replacement map had literal characters instead of
  entities → `md()` injected raw HTML via `innerHTML` from LLM/doc content.
- **FIX**: numeric-entity escaper (`&#NN;` per char) — mangling-proof.
- **TEST → RESULT (PASS)**: `md('<img onerror …><script>')` outputs
  `&#60;img…&#60;script`; `window.__pwn` never set after restore render.

### BUG 3 — Conversation-open jitter
- **ROOT CAUSE**: per-paint forced scroll + every restored message animating.
- **FIX**: animation only on `.msg.live`; single `scrollBottom()` after batch.
- **TEST → RESULT (PASS)**: open-conv restore + message-count regression in
  suite; zero console errors across the run.

### BUG 4 — Theme flash
- **ROOT CAUSE**: theme applied by end-of-body script → first-paint flash.
- **FIX**: pre-paint resolver `<script>` in `<head>` reading the store.
- **RESULT: PARTIAL** — logic correct and reload-tested, but sub-100 ms paint
  timing is not asserted in headless; verify visually in Safari.

### BUG 5 — Streaming scroll UX (subcase of 1)
- Covered by the scheduleFollow regressions above. **PASS**.

## Known remaining (honest, not hidden)
- **NOT TESTABLE here**: Safari/iOS real-device scroll + keyboard behavior
  (headless Chromium ≠ Mobile Safari). Manual checklist provided in README;
  the layout now uses the standard structural fixes Safari needs.
- **NOT TESTED**: jump-pill position with a 200 px-grown composer (logic
  positions it relative to composer-wrap; no automated case).
- **git commit not created** — git is not installed on this machine
  (`xcode-select` CLT missing). Commands recorded in FRONTEND_AUDIT.md §12.
