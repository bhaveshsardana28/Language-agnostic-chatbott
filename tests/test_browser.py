"""Real-browser UI tests (Playwright/Chromium) against the running GAIA v2 app.

Deterministic paths only: the campus-KB route needs no LLM key, so these
tests are stable. LLM-dependent rendering is verified in the live battery.

Run (server must be up on :8000):
    venv/bin/python tests/test_browser.py
"""

import os
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"


def run(pw):
    browser = pw.chromium.launch()
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(f"{'PASS' if cond else 'FAIL':68s} {name}")

    # ---------- desktop ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    page.goto(BASE)
    page.wait_for_selector("#welcome.show", timeout=8000)
    check("welcome screen visible on fresh load", page.is_visible("#welcome.show"))

    # suggestion card sends a real message (campus route = deterministic, keyless)
    page.fill("#input", "when are my exams")
    page.press("#input", "Enter")
    page.wait_for_selector(".msg.assistant .bubble", timeout=30000)
    page.wait_for_function(
        "document.querySelector('.msg.assistant .bubble').textContent.length > 20",
        timeout=30000)
    reply = page.text_content(".msg.assistant .bubble")
    check("campus reply rendered (mentions exams/ERP)", "exam" in reply.lower() or "erp" in reply.lower())

    # conversation saved with auto title
    page.wait_for_selector(".conv.active", timeout=5000)
    title = page.text_content(".conv.active .t")
    check("sidebar shows auto-titled conversation", title and title.strip().lower().startswith("when"))

    # message action: copy exists; debug card hidden by default
    check("actions row present on assistant message", page.locator(".acts-row").count() >= 1)
    check("debug card hidden when debug off", page.locator(".debug-card:visible").count() == 0)
    page.click("#debug-btn")
    check("debug card visible when debug on",
          page.locator(".debug-card:visible").count() >= 1 and
          "campus_kb" in page.text_content(".debug-card"))
    page.click("#debug-btn")

    # markdown / code block rendering
    page.fill("#input", "Write a Python hello world function in a code block")
    page.press("#input", "Enter")
    page.wait_for_selector(".codeblock", timeout=60000)
    check("code block rendered with language label + copy",
          "python" in page.text_content(".codeblock .cb-head").lower()
          and page.locator(".cb-copy").count() >= 1)

    # theme toggle
    before = page.get_attribute("html", "data-theme")
    page.click("#theme-btn")
    page.wait_for_timeout(150)
    after = page.get_attribute("html", "data-theme")
    check("theme toggles dark<->light", before != after)

    # document upload via the real input
    doc_path = os.path.abspath("data/test_upload_tmp.txt")
    with open(doc_path, "w") as f:
        f.write("Alpha policy: refunds within 30 days. Beta: shipping free over 50 euros. ")
    page.set_input_files("#file-input", doc_path)
    page.wait_for_selector("#doc-strip.show .chip.ok", timeout=30000)
    check("document chip shows Ready state", "chunks" in page.text_content("#doc-strip"))

    # no horizontal overflow at desktop
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("no horizontal overflow @1280", overflow <= 1)

    # second conversation + switch keeps history
    page.click("#new-chat")
    page.wait_for_selector("#welcome.show", timeout=5000)
    check("new chat returns to welcome, old chat preserved", page.locator(".conv").count() >= 2)
    # sidebar sorts by recency: the OLD conversation is the 2nd item now
    page.click(":nth-match(.conv, 2)")
    page.wait_for_timeout(300)
    check("switching back restores messages", page.locator(".msg").count() >= 3)

    # ---------- mobile ----------
    m = browser.new_context(viewport={"width": 375, "height": 667},
                            is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(BASE)
    mp.wait_for_selector("#menu-btn", timeout=8000)
    check("mobile: hamburger visible", mp.is_visible("#menu-btn"))
    check("mobile: sidebar hidden by default", not mp.is_visible(".sidebar .conv, .sidebar.open"))
    mo = mp.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("no horizontal overflow @375", mo <= 1)
    mp.click("#menu-btn")
    mp.wait_for_selector(".sidebar.open", timeout=3000)
    check("mobile: drawer opens", mp.is_visible(".sidebar.open"))
    mp.click("#scrim")
    mp.wait_for_timeout(250)
    check("mobile: scrim closes drawer", not mp.is_visible(".sidebar.open"))
    # composer usable on mobile
    mp.fill("#input", "hola")
    check("mobile: composer accepts input", mp.input_value("#input") == "hola")

    # ---------- errors visible? ----------
    check("no JS page/console errors during session", len(errors) == 0)
    if errors:
        print("   JS errors:", errors[:3])

    os.remove(doc_path)
    browser.close()

    fails = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fails)}/{len(results)} browser tests passed"
          + ("" if not fails else f" — FAILED: {fails}"))
    return 0 if not fails else 1


if __name__ == "__main__":
    with sync_playwright() as pw:
        sys.exit(run(pw))
