"""Offline Phase 2 browser/contrast checks. No application server or API key needed.

Run: python scripts/verify_design_system.py [--capture]
Uses the previously approved Playwright + Chromium. --capture writes review
screenshots and a JSON evidence report; otherwise no project files are written.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = "gaia.redesign.v2"
PASSED = []
CONTRAST = {}
RENDERED_CONTRAST = {}
FONTS = {}
SCREENSHOTS = []


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def passed(name):
    PASSED.append(name)
    print(f"PASS {name}")


def settled(page):
    page.evaluate("document.fonts.ready")
    page.wait_for_function("""() => document.getAnimations().every(a =>
        a.effect.getTiming().iterations === Infinity || a.playState !== 'running')""")


def shot(page, name, capture, full_page=True):
    if capture:
        settled(page)
        path = ROOT / "docs/screenshots/phase2" / f"{name}.png"
        page.screenshot(path=str(path), full_page=full_page, animations="disabled")
        SCREENSHOTS.append(str(path.relative_to(ROOT)))


def no_overflow(page, selector="html"):
    assert page.locator(selector).evaluate("e => e.scrollWidth <= e.clientWidth + 1"), selector


def luminance(hex_color):
    values = [int(hex_color.strip().lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(page, name, selector="html", voice=False):
    colors = page.locator(selector).evaluate("""e => Object.fromEntries([
      'page','surface','raised','soft','ink','muted','accent','action','on-action',
      'user','chip','chip-ink','danger','success','warning','disabled','disabled-ink',
      'code','selection','control-border','focus'
    ].map(key => [key, getComputedStyle(e).getPropertyValue('--color-' + key).trim()]))""")
    if voice:
        pairs = [(fg, "surface", 4.5) for fg in ("ink", "muted", "accent")]
        pairs += [("on-action", "action", 4.5), ("ink", "selection", 4.5), ("focus", "surface", 3), ("control-border", "surface", 3)]
    else:
        pairs = [("ink", bg, 4.5) for bg in ("page", "surface", "raised", "soft", "user", "code", "selection")]
        pairs += [(fg, bg, 4.5) for fg in ("muted", "accent") for bg in ("page", "surface", "raised", "soft")]
        pairs += [(fg, "surface", 4.5) for fg in ("danger", "success", "warning")]
        pairs += [("chip-ink", "chip", 4.5), ("on-action", "action", 4.5), ("disabled-ink", "disabled", 4.5)]
        pairs += [(fg, bg, 3) for fg in ("focus", "control-border") for bg in ("page", "surface", "raised", "soft")]
    rows = []
    for foreground, background, threshold in pairs:
        high, low = sorted([luminance(colors[foreground]), luminance(colors[background])], reverse=True)
        ratio = (high + .05) / (low + .05)
        row = dict(foreground=foreground, background=background, fg=colors[foreground], bg=colors[background],
                   ratio=round(ratio, 3), minimum=threshold)
        rows.append(row)
        assert ratio >= threshold, f"{name}: {row}"
    CONTRAST[name] = rows
    passed(f"{name}: {len(rows)} computed contrast pairs meet their thresholds")


def font_evidence(page, context):
    page.evaluate("document.fonts.load('400 16px \"DM Sans\"', 'Łódź')")
    settled(page)
    faces = page.evaluate("""() => [...document.fonts].map(f => ({family:f.family, weight:f.weight, status:f.status}))""")
    assert len(faces) == 4 and all(f["status"] == "loaded" for f in faces), faces
    session = context.new_cdp_session(page)
    session.send("DOM.enable")
    session.send("CSS.enable")
    root = session.send("DOM.getDocument")["root"]["nodeId"]
    for lang in ("en", "hi", "pa", "de", "es", "fr", "it", "ar", "zh", "ja", "ko", "ru"):
        node = session.send("DOM.querySelector", {"nodeId": root, "selector": f'.specimen p[lang="{lang}"]'})
        fonts = session.send("CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]})["fonts"]
        assert fonts and all(f["glyphCount"] > 0 for f in fonts), (lang, fonts)
        FONTS[lang] = fonts
    for lang, family in (("en", "DM Sans"), ("hi", "Noto Sans Devanagari"), ("pa", "Noto Sans Gurmukhi")):
        assert any(family in f["familyName"] and f["isCustomFont"] for f in FONTS[lang]), FONTS[lang]
    assert page.locator('.specimen p[lang="ar"]').evaluate("e => getComputedStyle(e).direction") == "rtl"
    session.detach()
    passed("four local font faces loaded; actual Indic/Latin custom glyph fonts and Arabic RTL verified")


def interactions(page, theme, capture):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator("#tab-conversation").click()
    page.keyboard.press("ArrowRight")
    expect(page.locator("#tab-welcome")).to_be_focused()
    expect(page.locator("#panel-welcome")).to_be_visible()
    page.keyboard.press("End")
    expect(page.locator("#tab-scripts")).to_be_focused()
    page.keyboard.press("Home")
    expect(page.locator("#tab-conversation")).to_be_focused()
    passed(f"{theme}: tabs support arrows/Home/End, focus and panel selection")

    menu = page.locator("#conversation-menu-button")
    menu.focus()
    page.keyboard.press("ArrowDown")
    expect(page.get_by_role("menuitem").first).to_be_focused()
    page.keyboard.press("End")
    expect(page.get_by_role("menuitem").last).to_be_focused()
    page.keyboard.press("Escape")
    expect(menu).to_be_focused()
    expect(page.locator("#conversation-menu")).to_be_hidden()
    menu.click()
    page.get_by_role("menuitem", name="Check script typography").click()
    expect(page.locator("#tab-scripts")).to_be_focused()
    page.locator("#tab-conversation").click()
    passed(f"{theme}: menu keyboard navigation, Escape return and action focus")

    copy = page.get_by_role("button", name="Copy English sample reply", exact=True)
    copy.focus()
    tooltip = page.locator("#tooltip-copy-en")
    expect(tooltip).to_be_visible()
    tooltip.hover()
    expect(tooltip).to_be_visible()
    page.keyboard.press("Escape")
    expect(tooltip).to_be_hidden()
    copy.click()
    expect(page.locator("#toast-region")).to_contain_text("copied as text")
    clipboard = page.evaluate("navigator.clipboard.readText()")
    assert clipboard == page.locator("#reply-en").inner_text()
    page.get_by_role("button", name="Dismiss notification").click()
    expect(page.locator("#toast-region .toast")).to_have_count(0)
    passed(f"{theme}: hover/focus tooltip, Escape dismissal and exact text clipboard copy")

    message = page.locator("#preview-message")
    message.fill("")
    message.press("Enter")
    expect(message).to_have_attribute("aria-invalid", "true")
    expect(page.locator("#composer-error")).to_be_visible()
    message.fill("A thought")
    message.press("Shift+Enter")
    message.press("i")
    assert message.input_value() == "A thought\ni"
    message.press("Enter")
    expect(page.locator("#toast-region")).to_contain_text("no request was sent")
    expect(message).to_have_value("A thought\ni")
    page.get_by_role("button", name="Dismiss notification").click()
    page.get_by_role("button", name="Preview the thinking state", exact=True).click()
    expect(page.locator("#preview-reply")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_role("button", name="Copy German sample reply")).to_be_disabled()
    expect(page.locator("#preview-reply")).to_have_attribute("aria-busy", "false", timeout=5000)
    expect(page.get_by_role("button", name="Copy German sample reply")).to_be_enabled()
    expect(page.locator("#toast-region")).to_contain_text("Thinking preview finished")
    passed(f"{theme}: composer errors/newlines/draft retention and explicit disabled/loading states")

    opener = page.get_by_role("button", name="Open appearance settings", exact=True)
    opener.click()
    dialog = page.locator("#settings-dialog")
    expect(dialog).to_be_visible()
    for _ in range(12):
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.closest('dialog')?.id") == "settings-dialog"
    message.evaluate("e => e.focus()")
    assert page.evaluate("document.activeElement.closest('dialog')?.id") == "settings-dialog"
    done = dialog.get_by_role("button", name="Done", exact=True)
    done.focus()
    done.hover()
    assert done.evaluate("e => getComputedStyle(e).outlineWidth") == "3px"
    # Measure the rendered interaction state, not just the intended token pair.
    colors = done.evaluate(r"""e => {
      const style = getComputedStyle(e);
      const hex = value => '#' + value.match(/\d+/g).slice(0, 3)
        .map(n => Number(n).toString(16).padStart(2, '0')).join('');
      return {fg:hex(style.color), bg:hex(style.backgroundColor)};
    }""")
    high, low = sorted([luminance(colors["fg"]), luminance(colors["bg"])], reverse=True)
    ratio = (high + .05) / (low + .05)
    assert ratio >= 4.5, (theme, colors, ratio)
    RENDERED_CONTRAST[theme] = {"state": "primary button, hover + keyboard focus", **colors,
                                "ratio": round(ratio, 3), "minimum": 4.5}
    passed(f"{theme}: rendered primary hover + focus contrast {ratio:.3f}:1 and 3px focus ring")
    shot(page, f"{theme}-1440-settings", capture, False)
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    expect(opener).to_be_focused()
    passed(f"{theme}: named native modal traps keyboard focus, makes background inert, restores opener")

    page.get_by_role("button", name="Open sample collection", exact=True).click()
    search = page.locator("#collection-search")
    search.fill("unmatched")
    expect(page.locator("#empty-search")).to_be_visible()
    expect(page.locator("#sample-conversation")).to_be_hidden()
    search.fill("language")
    expect(page.locator("#sample-conversation")).to_be_visible()
    page.locator("#tab-documents").click()
    shot(page, f"{theme}-1440-drawer", capture, False)
    page.locator("#upload-preview").click()
    expect(page.locator("#library-drawer .toast-inline")).to_contain_text("No file was uploaded")
    page.mouse.click(1000, 400)
    expect(page.locator("#library-drawer")).to_be_hidden()
    expect(page.get_by_role("button", name="Open sample collection", exact=True)).to_be_focused()
    passed(f"{theme}: searchable drawer, documents empty state, in-dialog toast and backdrop close")

    opener.click()
    other = "dark" if theme == "light" else "light"
    page.get_by_role("radio", name=other.title(), exact=True).check()
    expect(page.locator("html")).to_have_attribute("data-theme", other)
    page.locator("#reduce-motion").check()
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", other)
    expect(page.locator("html")).to_have_attribute("data-motion", "reduced")
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == "legacy sentinel"
    page.get_by_role("button", name="Open voice preview, microphone off", exact=True).click()
    expect(page.locator(".voice-orb")).to_be_hidden()
    expect(page.locator(".voice-reduced-icon")).to_be_visible()
    assert page.evaluate("document.getAnimations().length") == 0
    page.locator("#voice-state").select_option("listening")
    expect(page.locator("#voice-state-label")).to_contain_text("Listening · design preview")
    if theme == "light":
        shot(page, "voice-reduced-motion", capture, False)
    page.keyboard.press("Escape")
    expect(page.locator("#voice-dialog")).to_be_hidden()
    passed(f"{theme}: persistent theme/motion, legacy storage isolation, reduced-motion icon/state")

    opener.click()
    page.locator("#reset-preferences").click()
    expect(dialog.locator(".toast-inline")).to_contain_text("Preview preferences reset")
    assert page.evaluate(f"localStorage.getItem('{KEY}')") is None
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == "legacy sentinel"
    page.keyboard.press("Escape")
    expect(dialog).to_be_hidden()
    page.emulate_media(reduced_motion="reduce")
    expect(page.locator("html")).to_have_attribute("data-motion", "reduced")
    page.emulate_media(color_scheme=other)
    expect(page.locator("html")).to_have_attribute("data-theme", other)
    page.locator("#preview-message").fill("Timer check")
    page.locator("#preview-message").press("Enter")
    expect(page.locator("#toast-region .toast")).to_have_count(1)
    # Do not hover/focus the notification: expiry must work without animationend.
    expect(page.locator("#toast-region .toast")).to_have_count(0, timeout=7000)
    passed(f"{theme}: scoped reset, live OS preferences and toast expiry with motion disabled")


def run(origin, capture):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        version = browser.version
        for theme in ("light", "dark"):
            context = browser.new_context(color_scheme=theme, reduced_motion="no-preference",
                                          permissions=["clipboard-read", "clipboard-write"])
            context.add_init_script("""if (!sessionStorage.getItem('test-seeded')) {
                localStorage.setItem('gaia.store.v1', 'legacy sentinel');
                sessionStorage.setItem('test-seeded', 'true');
              }
              window.previewMediaCalls = 0;
              navigator.mediaDevices.getUserMedia = () => { window.previewMediaCalls++; throw Error('Unexpected microphone request'); };
              speechSynthesis.speak = () => { window.previewMediaCalls++; throw Error('Unexpected speech request'); };
            """)
            page = context.new_page()
            errors, bad_assets, requests = [], [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("response", lambda response: bad_assets.append(response.url) if response.status >= 400 else None)
            page.on("request", lambda request: requests.append((request.method, request.url)))
            page.goto(origin + "/v2/components.html")
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            contrast(page, theme)
            for width in (360, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                for screen in ("conversation", "welcome", "scripts"):
                    page.locator(f"#tab-{screen}").click()
                    settled(page)
                    no_overflow(page)
                    assert page.locator(f"#panel-{screen}").is_visible()
                    for button in page.get_by_role("button").all():
                        if button.is_visible():
                            assert button.get_attribute("aria-label") or button.inner_text().strip(), button
                            assert button.bounding_box()["height"] >= 44, button
                    shot(page, f"{theme}-{width}-{screen}", capture and width in (360, 1440))
                if width == 1440 and theme == "light":
                    font_evidence(page, context)
                page.locator("#tab-conversation").click()
                page.get_by_role("button", name="Open voice preview, microphone off", exact=True).click()
                settled(page)
                no_overflow(page, "#voice-dialog")
                assert abs(page.locator("#voice-dialog").bounding_box()["width"] - width) < 1
                assert page.evaluate("document.elementFromPoint(innerWidth - 1, 1).closest('.voice-mode')?.id") == "voice-dialog"
                for state in ("idle", "listening", "thinking", "speaking"):
                    page.locator("#voice-state").select_option(state)
                    expect(page.locator("#voice-state-label")).to_contain_text(state.title())
                page.locator("#voice-state").select_option("idle")
                if width == 1440:
                    contrast(page, f"voice-with-{theme}-app", "#voice-dialog", voice=True)
                shot(page, f"{theme}-{width}-voice", capture and width in (360, 1440), False)
                page.keyboard.press("Escape")
                expect(page.locator("#voice-dialog")).to_be_hidden()
                assert page.evaluate("window.previewMediaCalls") == 0
                expect(page.locator("html")).to_have_attribute("data-theme", theme)
                assert page.locator("html").evaluate("e => getComputedStyle(e).getPropertyValue('--color-action').trim()") != "#dafa68"
                passed(f"{theme}/{width}px: three screens fit, controls labelled/44px, four voice states, Signal scoped")
            interactions(page, theme, capture)
            assert page.evaluate("window.previewMediaCalls") == 0
            assert not errors and not bad_assets, (errors, bad_assets)
            assert all(method == "GET" and url.startswith(origin + "/v2/") for method, url in requests), requests
            passed(f"{theme}: zero console/page/asset failures; only local static GETs; no mic or speech calls")
            context.close()

        # Recovery is tested in a fresh context, independent of the happy path.
        for mode in ("malformed", "blocked"):
            context = browser.new_context(color_scheme="dark", reduced_motion="reduce")
            if mode == "malformed":
                context.add_init_script(f"localStorage.setItem('{KEY}', '{{bad json');")
            else:
                context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('Blocked', 'SecurityError');}});")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/v2/components.html")
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            expect(page.locator("html")).to_have_attribute("data-motion", "reduced")
            page.locator("#theme-toggle").click()
            expect(page.locator("html")).to_have_attribute("data-theme", "light")
            if mode == "blocked":
                expect(page.locator("#toast-region")).to_contain_text("storage is unavailable")
            assert not errors, errors
            passed(f"{mode} preferences: system-safe first paint and usable theme switch")
            context.close()
        browser.close()
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    if args.capture:
        (ROOT / "docs/screenshots/phase2").mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "static")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        version = run(f"http://127.0.0.1:{server.server_port}", args.capture)
    finally:
        server.shutdown()
        server.server_close()
    report = {"phase": 2, "scope": "offline component preview, not live app parity",
              "environment": {"platform": platform.platform(), "python": platform.python_version(), "chromium": version},
              "passed_groups": PASSED, "contrast": CONTRAST, "rendered_contrast": RENDERED_CONTRAST,
              "rendered_fonts": FONTS, "screenshots": SCREENSHOTS}
    if args.capture:
        (ROOT / "docs/design-system-checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"\n{len(PASSED)} check groups passed; {sum(map(len, CONTRAST.values()))} token contrast pairs; "
          f"{len(RENDERED_CONTRAST)} rendered contrast states; {len(SCREENSHOTS)} screenshots.")
    print(f"Chromium {version}; no live chat, RAG or voice quality claim.")


if __name__ == "__main__":
    main()
