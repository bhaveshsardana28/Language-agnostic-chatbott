# GAIA design system — Phase 2

**Status:** implemented beside the legacy application; not promoted to the
default route. The applied preview is
`static/v2/components.html`. It uses the approved **Common Ground** direction
for both app themes. **Signal** is deliberately contained inside the
immersive Voice Mode overlay.

The CSS and component workbench are the Phase 2 source of truth:

- `static/v2/css/tokens.css` — semantic tokens and theme scopes
- `static/v2/css/base.css` — reset, local font faces, script fallbacks and focus
- `static/v2/css/components.css` — reusable primitives and states
- `static/v2/css/layout.css` — workbench, conversation, welcome, script lab and voice overlay
- `static/v2/css/motion.css` — state motion, reduced motion and hidden-tab behavior
- `static/v2/js/{theme-init,preferences,motion,ui,workbench}.js` — preview-only behavior
- `docs/design-system-checks.json` — generated browser/contrast/font evidence
- `docs/screenshots/phase2/` — generated light/dark review screenshots

The legacy route, backend and legacy static files remain unchanged after the
pre-existing application snapshot commit `a0a7185`.

### Phase 3 adoption

The approved system now also powers `static/v2/index.html`, the application
shell. [PHASE_3_SHELL.md](PHASE_3_SHELL.md) documents its behavior and verification.
`shell.css` adds viewport/sidebar/composer layout while reusing the existing
component and editorial layout rules. `icons.js` mounts the **same inline
sprite** on both pages; `appearance.js` shares theme/motion control wiring.
Three matching sidebar/pause/play icons extend the original family.

`gaia.redesign.v2` now also contains the boolean `sideCollapsed`. The pre-paint
script resolves this alongside theme/motion, and changing appearance preserves
the collapse choice. Reset preview preferences resets all three preferences.
The Phase 2 report/screenshots below remain that phase's checkpoint; its full
battery was rerun after this shared-module extraction (35 groups passed).

## Product direction

Common Ground is an editorial, language-first conversation surface:

- paper and ink establish a calm reading canvas;
- sage carries user-authored content and soft utility surfaces;
- vermilion marks language movement, focus, selected tabs and primary action;
- Georgia is reserved for editorial display and reading moments;
- DM Sans carries interface labels, controls and metadata;
- language changes are shown as an explicit divider, rather than a hidden state;
- voice can become atmospheric without changing the app's identity.

The dark app theme is a designed palette with its own semantic values. It is
not an inversion/filter and it does not borrow Signal's chartreuse treatment.
Signal uses graphite and chartreuse only under `.voice-mode`, so the exception
cannot leak into normal conversation, welcome or document surfaces.

## Token contract

### Color semantics

| Semantic role | Light | Dark | Voice overlay |
|---|---|---|---|
| Page | `#f4f2ed` | `#171c18` | `#111510` |
| Surface | `#fcfbf8` | `#202720` | `#111510` |
| Raised | `#ffffff` | `#2a3129` | `#20261b` |
| Soft | `#e9ece2` | `#2b342b` | `#20261b` |
| Ink | `#292e2a` | `#eeeade` | `#f0f2e8` |
| Muted | `#5c645a` | `#b7beac` | `#a1a997` |
| Accent | `#aa3925` | `#efa18b` | `#dafa68` |
| Primary action | `#b7412b` | `#d68c76` | `#dafa68` |
| On primary action | `#ffffff` | `#1d211b` | `#111510` |
| User surface | `#e6e9dc` | `#354031` | inherited |
| Control border | `#788071` | `#87907c` | `#768268` |
| Focus | `#8b3525` | `#f2bda1` | `#dafa68` |
| Selection | `#ead6c9` | `#654739` | `#344220` |

Status and supporting values are also semantic tokens: `--color-danger`,
`--color-success`, `--color-warning`, `--color-disabled`, `--color-code`,
`--color-chip` and `--color-chip-ink`. Components consume these names rather
than hard-coded theme colors.

### Layout, type and shape

| Group | Contract |
|---|---|
| Spacing | 4px base scale: `--space-1` through `--space-24` |
| Controls | 44px minimum block size; 20px default icon; 36px avatar |
| Shape | 4px small radius, 8px medium radius, 12px dialog radius, round avatars |
| Reading | `--reading-width: 70ch`; `--line-reading: 1.75` |
| Display | `--text-hero: clamp(2.75rem, 5vw, 4.5rem)`; tight editorial leading |
| UI type | DM Sans local WOFF2, 400–700 variable range |
| Editorial type | Georgia/system serif stack |
| Script type | local Noto Sans Devanagari and Gurmukhi; system Arabic, CJK and Cyrillic stacks |
| Layers | content 0, sticky 10, menu 20, tooltip 30, toast 40; native dialogs use the top layer |

### Motion

| Token | Value | Use |
|---|---:|---|
| `--motion-fast` | 150ms | dismissal and small feedback |
| `--motion-ui` | 220ms | overlay/toast entrance and prompt icon transitions |
| `--motion-slow` | 300ms | reserved for later slower state changes |
| `--motion-panel` | 420ms | drawer spring sample |
| `--motion-ambient` | 3200ms | Voice Mode breathing loop |
| `--motion-shimmer` | 1400ms | thinking skeleton |
| `--spring-mass` / `--spring-stiffness` / `--spring-damping` | `1 / 260 / 28` | sampled drawer response |

Only `transform` and `opacity` animate. The drawer samples the declared
physical values into WAAPI keyframes; it does not claim that CSS has a native
spring implementation. `visibilitychange` pauses ambient CSS loops and
finishes short JS transitions. `data-visibility="hidden"` is also available
for page-level CSS consumers.

Reduced motion is honored from both `prefers-reduced-motion: reduce` and the
settings checkbox. The app writes only the following isolated preference
object to `localStorage` under `gaia.redesign.v2`:

```json
{"theme":"light|dark|system","reduceMotion":false}
```

It never reads or mutates the legacy `gaia.store.v1` application state.

## Brand and icons

`components.html` includes one original inline SVG symbol sprite, used by all
interface icons. Icons share a 24-unit viewBox, 1.5-unit stroke, round caps and
joins, and inherit `currentColor`. The original 32-unit GAIA monogram is used
in the header and assistant avatar; `assets/brand/favicon.svg` carries the same
mark. Two original 168-unit line illustrations serve the empty-conversation
and empty-document states. No icon package or external image request is needed.

## Components in use

The workbench uses each required primitive in a realistic screen or overlay:

| Primitive | Applied use and state coverage |
|---|---|
| Button | primary preview, quiet action, danger/reset, disabled during thinking |
| IconButton | rail, theme, settings, copy, voice, menu and dismiss controls |
| Input / Textarea | collection search and composer with empty/error/draft states |
| Dialog | named appearance settings and Voice Mode top-layer overlays |
| Drawer | searchable conversation collection and documents empty state |
| Toast | live region, dismiss button, timeout, hover/focus pause and in-dialog placement |
| Tooltip | copy affordances on focus and pointer with Escape dismissal |
| Chip | language/script and illustrative metadata labels |
| Skeleton | thinking preview with `aria-busy` and explicit no-request status |
| Avatar | user initials and GAIA assistant mark |
| Menu | conversation actions with roving menu focus and type-ahead |
| Tabs | screen tabs and collection tabs with roving `tabindex` |

Interaction behavior is intentionally preview-only. The composer validates and
retains a local draft but never sends a request. Copy uses the Clipboard API
only when available and reports a manual-copy fallback. The document control
reports that no file was uploaded. Voice state selection changes illustrated
labels only; it never requests a microphone, speech recognition, waveform data
or audio playback.

## Accessibility behavior

- A skip link moves focus to the applied screen.
- Icon-only controls have accessible names; other actions have visible text labels.
- Dialogs have `aria-labelledby`, native top-layer behavior, Escape close,
  backdrop close and a focus trap; closing restores the opener when connected.
- Tabs use `aria-selected`, `aria-controls`, roving `tabindex`, arrows, Home and
  End. Menus use `role="menu"`, `role="menuitem"`, arrows, Home/End, type-ahead,
  Escape and focus return.
- Status text uses live regions for thinking, search and toast feedback.
- The assistant loading state is represented by `aria-busy`; it is not presented
  as backend latency.
- `dir="auto"`, `lang` and script-specific line-height/font rules are applied
  to multilingual specimens and sample messages.
- Focus rings are 3px with a 3px offset. Primary hover styling does not obscure
  the focus ring.
- Controls are checked at a 44px minimum block size in the preview browser
  battery.
- When motion is reduced, the Voice orb becomes a static voice icon and the
  state label remains available. CSS loops and JS transitions are disabled.

## Contrast evidence

The following table summarizes the computed token measurements generated by
`scripts/verify_design_system.py`, using the WCAG relative-luminance formula.
It reports the lowest measured ratio for each family, not a palette-tool claim.
The full foreground/background rows are in `docs/design-system-checks.json`.

| Scope | Pair family | Lowest ratio | Required | Result |
|---|---|---:|---:|---|
| Light app | ink / page, surface, raised, soft, user, code, selection | 9.852 | 4.5:1 | PASS |
| Light app | muted / page, surface, raised, soft | 5.126 | 4.5:1 | PASS |
| Light app | accent / page, surface, raised, soft | 5.288 | 4.5:1 | PASS |
| Light app | status, chip and disabled pairs | 5.153 | 4.5:1 | PASS |
| Light app | white on action | 5.520 | 4.5:1 | PASS |
| Light app | focus / page, surface, raised, soft | 6.668 | 3:1 | PASS |
| Light app | control border / page, surface, raised, soft | 3.427 | 3:1 | PASS |
| Dark app | ink / page, surface, raised, soft, user, code, selection | 6.946 | 4.5:1 | PASS |
| Dark app | muted / page, surface, raised, soft | 6.738 | 4.5:1 | PASS |
| Dark app | accent / page, surface, raised, soft | 6.226 | 4.5:1 | PASS |
| Dark app | status, chip and disabled pairs | 6.206 | 4.5:1 | PASS |
| Dark app | dark ink on action | 6.123 | 4.5:1 | PASS |
| Dark app | focus / page, surface, raised, soft | 7.717 | 3:1 | PASS |
| Dark app | control border / page, surface, raised, soft | 3.874 | 3:1 | PASS |
| Voice overlay | ink, muted, accent, action and focus | 7.586 | 4.5:1 | PASS |
| Voice overlay | ink / selection | 9.542 | 4.5:1 | PASS |
| Voice overlay | control border / surface | 4.535 | 3:1 | PASS |

The final run measured **72 pairs**: 29 light-app pairs, 29 dark-app pairs,
and 7 pairs for each Voice overlay context. Focus and control borders use the
3:1 non-text/UI threshold where applicable. No contrast assertion is based on
an animation midpoint; the browser battery settles or disables motion before
measurement.

Two additional checks inspect actual rendered foreground/background colors
while the primary button is **both hovered and keyboard-focused**, not just
its intended token values: **5.520:1 light** and **6.123:1 dark**, with the 3px
focus ring retained. This caught and fixed a generic hover-rule override that
the token-only audit could not detect. These rows appear under
`rendered_contrast` in the report.

## Typography and script evidence

The four local WOFF2 assets are unmodified downloads documented in
`static/v2/assets/fonts/README.md`, with the SIL Open Font License and notices
in `OFL.txt`:

- DM Sans Latin and Latin Extended
- Noto Sans Devanagari
- Noto Sans Gurmukhi

The browser check loaded all four faces and inspected platform glyph coverage
for English, German, Spanish, French, Italian, Hindi, Punjabi, Arabic, Chinese,
Japanese, Korean and Cyrillic. The final macOS capture used Noto for Indic,
Geeza Pro for Arabic, PingFang SC/Hiragino Sans/Apple SD Gothic Neo for CJK,
and SF for Cyrillic. The earlier Linux review used FreeSerif for Arabic.
System fallback availability remains device-dependent. These are rendering checks,
not native-speaker language-quality or language-detection claims.

## Applied preview and evidence

The preview is served through the existing FastAPI static mount:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://localhost:8000/static/v2/components.html
```

If port 8000 is occupied, inspect it before starting another server:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

From a second Terminal on macOS, the Phase 2 checks are:

```bash
cd /Users/bhaveshsardana/language_agnostic_chatbot
source venv/bin/activate
python scripts/verify_design_system.py --capture
python -m pytest -q
python tests/test_code_switching.py
git diff --check
```

The check script starts its own temporary static server, tests light and dark
themes at 360, 768, 1024 and 1440px, captures the 21 review screenshots, and
writes `docs/design-system-checks.json`. It does not call the chat API. The
final result was **35 check groups passed, 72 token contrast pairs passed,
2 rendered contrast states passed, 21 screenshots**, with Chromium
153.0.8010.12 on **macOS 27.0.1 ARM64**, Python 3.12.7. Earlier runs in the
Linux ARM64 sandbox used Python 3.12.15. The report records the final platform.

The project regression suite remained **21 passed, 1 warning in 2.02s**. The separate
detector runner remained **28 checks passed**. The unmodified legacy browser
runner still has its previously documented result: welcome passes and the
chat assertion times out after 30 seconds because of the preserved
`static/js/markdown.js` parse error and related legacy initialization defects.
It was not weakened or replaced by the Phase 2 preview.

For the legacy diagnosis, run:

```bash
python scripts/diagnose_frontend_startup.py
python tests/test_browser.py
```

The diagnostic directly checked the campus API route and observed no browser
chat POST after Enter. It creates and deletes only its own diagnostic
conversation. See `docs/STARTUP_FAILURE.md` for the exact evidence and
preservation checkpoint.

## Scope boundary

Phase 2 establishes the system and its used primitives beside the old route.
It does not claim live chat, RAG retrieval quality, document upload behavior,
conversation persistence, multilingual answer quality, speech recognition,
text-to-speech or real microphone support. Those are later phases and remain
gated by the Phase 0 parity checklist in `docs/FRONTEND_AUDIT.md`.

## Historical legacy design note

The earlier design-system document described the pre-redesign values in
`templates/index.html` and `static/css/tokens.css`. Those values are retained
in the legacy snapshot for reproducibility and were intentionally not copied
into this Phase 2 contract. The old route remains available until the complete
parity and sign-off phase authorizes promotion.

<details>
<summary>Archived pre-redesign document — historical claims, not current verification</summary>

The original text below is preserved from `a0a7185`. Its inline-template source
location and past verification claims are historical; the Phase 0 audit
supersedes them. In particular, no axe run or live-script certification is
claimed by the current Phase 2 work.

# Design System — GAIA

Source of truth: `templates/index.html` (tokens at lines ~16–40). Every
number below was computed this session (WCAG 2.1 relative-luminance formula)
— not copied from a palette tool.

## Tokens

| Group | Tokens |
|---|---|
| Spacing (4px base) | `--sp-1:4px … --sp-6:32px` |
| Type scale | `--fs-xs .72rem · --fs-s .82rem · --fs-m .93rem · --fs-l 1.05rem · --fs-xl 1.4rem` |
| Radius | `--r-s 8px · --r-m 12px · --r-l 16px` |
| Motion | `--t-fast 150ms · --t-med 250ms · --ease cubic-bezier(.2,.7,.3,1)` |
| Z-index ladder | `--z-jump 5 · --z-drawer 35 · --z-scrim 36 · --z-modal 50 · --z-toast 60` |
| Primary accent | `--accent` (text/interactive) · `--accent-strong` (solid buttons: white text ≥5.17:1) · `--accent-2` |
| Secondary accent | `--lang` (language indicators ONLY — never for actions) |
| Status | `--danger · --ok · --warn` (theme-aware for AA) |
| Surfaces | `--bg · --surface · --surface2 · --border · --text · --muted · --shadow` |

## Color themes (both AA-audited)

| Role | Dark | Light |
|---|---|---|
| bg | `#0d0f12` | `#f6f7f9` |
| surface / surface2 | `#16181d` / `#1c1f26` | `#ffffff` / `#eef0f3` |
| text / muted | `#e9ebf0` / `#9aa0ae` | `#171a20` / `#5b6472` |
| accent | `#5c9df8` | `#1d4ed8` |
| accent-strong | `#2563eb` | `#2563eb` |
| lang | `#2dd4bf` | `#0f766e` |
| danger / ok / warn | `#ef4444` / `#34d399` / `#f59e0b` | `#b91c1c` / `#047857` / `#b45309` |

### Measured contrast (WCAG AA, ≥4.5:1 text)

**Dark** — all PASS: text/bg 16.09 · text/surface 14.89 · muted/bg 7.32 ·
muted/surface2 6.29 · accent/bg 6.98 · accent/surface2 5.99 · accent/surface
5.66* · lang/surface 9.54 · danger/surface 4.72 · ok/bg 9.98 · warn/surface
8.27 · **white on accent-strong 5.17** · dark-on-red confirm 5.10.
(*recomputed with `--accent #5c9df8`)

**Light** — all PASS after this phase's fixes (accent, danger, ok, warn,
muted were darkened): text/bg 16.26 · muted/surface2 5.24 · accent/bg 6.25 ·
danger/surface 6.47 · ok/surface 5.48 · warn/bg 4.68 · lang/surface 5.47 ·
white on red 6.47 · white on accent-strong 5.17.

**Design decisions locked by measurement:**
1. Light theme uses darker accent/status hues for *text* (the dark-theme
   hues failed AA on white: accent 3.43:1, ok 1.92:1).
2. No single dark-theme red passes both text-on-surface (≥4.5) and
   white-on-red (≥4.5) — verified numerically — so the delete-confirm
   button uses near-black text on red in dark mode (5.10:1).
3. Hover states never change the *pairing*: `#new-chat:hover` keeps
   accent-strong + adds a shadow (white-on-accent was 3.68:1 → rejected).

## Typography
`--font`: system stack + Noto Sans Devanagari + Noto Sans Gurmukhi fallbacks
— verified rendering for Devanagari/Gurmukhi in live batteries. All bubbles
use `dir="auto"`.

## Motion inventory (all state-explaining, none decorative)
message entrance (`.msg.live`, 180ms rise) · streaming caret blink ·
thinking pulse · modal pop (150ms) · toast fade · drawer slide (250ms) ·
mic pulse · send/stop button swap + press scale · theme color transition ·
welcome greeting crossfade + card stagger (welcome only).
Reduced motion: `prefers-reduced-motion` media query + in-app
"Reduce motion" setting both disable all of the above.

**Audit-methodology note (live-caught):** axe-core reports transient
contrast "violations" when it walks the DOM *during* entrance animations
(opacity mid-fade → blended foreground). This phase's two apparent findings
were exactly that — steady-state re-measurements are CLEAN in both themes
and all chip/bubble pairs pass numerically. Rule: settle ≥400ms (or disable
animations) before running axe. Recorded here so nobody "fixes" a
non-bug again.

## Component states
Buttons: idle / hover (shadow or border, never a failing color pairing) /
active (scale .94) / disabled (opacity .35 + not-allowed) / aria-pressed
(mic, debug). Inputs: idle / focus (accent ring via :focus-visible). Dialogs:
named (`aria-labelledby`), focus lands inside, Escape closes, pop animation.

</details>
