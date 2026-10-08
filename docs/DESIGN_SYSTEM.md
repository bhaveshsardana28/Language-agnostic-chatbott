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
