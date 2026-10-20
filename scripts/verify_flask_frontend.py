#!/usr/bin/env python3
"""Offline browser contract checks for the no-build Flask frontend.

Run: ./venv/bin/python scripts/verify_flask_frontend.py
Requires the already-installed Playwright Python package and Chromium. Every
request is fulfilled from project files or a queued /chat fixture, or blocked;
no server, Flask import, model, API key, installation, or screenshots are used.
Each case gets a fresh browser context. Failures are collected and exit nonzero.
"""

from collections import deque
from functools import partial
import json
import mimetypes
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Error as PlaywrightError, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://frontend.test"
TIMEOUT = 3000
USER = 'article.message[data-role="user"]'
ASSISTANT = 'article.message[data-role="assistant"]'
ERROR = 'article.message[data-role="error"]'
LANGUAGES = (
    ("en", "English", "Where is the library?", "The library is open."),
    ("hi", "Hindi|हिन्दी|हिंदी", "पुस्तकालय कहाँ है?", "पुस्तकालय खुला है।"),
    ("pa", "Punjabi|ਪੰਜਾਬੀ", "ਲਾਇਬ੍ਰੇਰੀ ਕਿੱਥੇ ਹੈ?", "ਲਾਇਬ੍ਰੇਰੀ ਖੁੱਲ੍ਹੀ ਹੈ।"),
    ("es", "Spanish|Español", "¿Dónde está la biblioteca?", "La biblioteca está abierta."),
    ("fr", "French|Français", "Où est la bibliothèque ?", "La bibliothèque est ouverte."),
    ("de", "German|Deutsch", "Wo ist die Bibliothek?", "Die Bibliothek ist geöffnet."),
)

# Observe forbidden APIs without replacing application behavior. The binding
# preserves observations across reloads, including caught storage exceptions.
AUDIT_SCRIPT = """(() => {
  const report = name => { void window.__frontendAudit(name); };
  for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) {
    const descriptor = Object.getOwnPropertyDescriptor(window, name);
    if (!descriptor || !descriptor.get || !descriptor.configurable)
      throw new Error('Cannot instrument ' + name);
    Object.defineProperty(window, name, {...descriptor, get() {
      report(name); return descriptor.get.call(this);
    }});
  }
  for (const prototype of [Element.prototype, ShadowRoot.prototype]) {
    const descriptor = Object.getOwnPropertyDescriptor(prototype, 'innerHTML');
    Object.defineProperty(prototype, 'innerHTML', {...descriptor,
      get() { report('innerHTML read'); return descriptor.get.call(this); },
      set(value) { report('innerHTML write'); descriptor.set.call(this, value); }
    });
  }
})();"""


def reply(text="A safe fixture reply.", language="en", confidence=0.83):
    return {"reply": text, "detected_language": language,
            "confidence": confidence, "intent": "library"}


def wait_for(page, predicate, description, timeout=TIMEOUT):
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, description
        page.wait_for_timeout(20)


class MissingContract(AssertionError):
    """The required shell is absent, so dependent checks cannot run."""


class Frontend:
    """File-only origin plus a FIFO of deliberately controlled chat responses."""

    def __init__(self, browser, width=1440):
        self.responses = deque()
        self.requests = []
        self.pending = []
        self.failed_requests = []
        self.unexpected = []
        self.errors = []
        self.console = []
        self.violations = []
        self.assets = set()
        self.expected_api_failures = 0
        self.ignored_console = 0
        self.context = browser.new_context(
            viewport={"width": width, "height": 900}, color_scheme="light",
            reduced_motion="reduce", service_workers="block",
        )
        self.context.expose_binding(
            "__frontendAudit", lambda _source, name: self.violations.append(name))
        self.context.add_init_script(AUDIT_SCRIPT)
        self.context.route("**/*", self.route)
        self.context.route_web_socket("**/*", self.block_socket)
        self.page = self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", self.record_console)
        self.page.on("requestfailed", lambda request: self.failed_requests.append(request))
        self.page.on("dialog", self.dismiss_dialog)

    def record_console(self, message):
        if message.type == "error":
            self.console.append((message.text, message.location.get("url", "")))

    def dismiss_dialog(self, dialog):
        self.errors.append(f"Unexpected {dialog.type} dialog: {dialog.message}")
        dialog.dismiss()

    def block_socket(self, socket):
        self.unexpected.append(f"WebSocket {socket.url}")
        socket.close()

    def enqueue(self, data=None, *, status=200, mode="json", body=None):
        self.responses.append({"data": data, "status": status, "mode": mode, "body": body})

    def route(self, route):
        request = route.request
        url = urlsplit(request.url)
        if f"{url.scheme}://{url.netloc}" != ORIGIN:
            self.unexpected.append(f"External request: {request.method} {request.url}")
            route.abort("blockedbyclient")
        elif url.path == "/chat":
            self.requests.append(request)
            if request.method != "POST" or not self.responses:
                self.unexpected.append(f"Unplanned API request: {request.method} /chat")
                route.abort("blockedbyclient")
                return
            response = self.responses.popleft()
            if response["mode"] == "hold":
                self.pending.append(route)
            elif response["mode"] == "network":
                self.expected_api_failures += 1
                route.abort("failed")
            else:
                if response["status"] >= 400:
                    self.expected_api_failures += 1
                route.fulfill(status=response["status"], content_type="application/json",
                              body=response["body"] if response["mode"] == "raw"
                              else json.dumps(response["data"], ensure_ascii=False))
        elif request.method == "GET" and url.path == "/":
            route.fulfill(content_type="text/html; charset=utf-8",
                          body=(ROOT / "templates/index.html").read_bytes())
        elif request.method == "GET" and url.path.startswith("/static/"):
            # urlsplit discards ?v=..., and resolve prevents escaping static/.
            path = (ROOT / unquote(url.path).lstrip("/")).resolve()
            if path.is_relative_to((ROOT / "static").resolve()) and path.is_file():
                self.assets.add(url.path)
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                route.fulfill(content_type=mime, body=path.read_bytes())
            else:
                self.unexpected.append(f"Missing/unsafe static asset: {url.path}")
                route.fulfill(status=404, body="Missing test fixture asset")
        elif request.method == "GET" and url.path == "/favicon.ico":
            route.fulfill(status=204)
        else:
            self.unexpected.append(f"Unexpected request: {request.method} {request.url}")
            route.abort("blockedbyclient")

    def open(self):
        self.page.goto(ORIGIN + "/", wait_until="load")

    def payload(self, index=-1):
        request = self.requests[index]
        assert request.method == "POST", "Chat must use POST"
        assert "application/json" in request.headers.get("content-type", ""), \
            "Chat must send JSON Content-Type"
        return json.loads(request.post_data)

    def send(self, message, language="", *, enter=False):
        count = len(self.requests)
        self.page.locator("#language-select").select_option(language)
        self.page.locator("#message-input").fill(message)
        expect(self.page.locator("#send-button")).to_be_enabled()
        if enter:
            self.page.locator("#message-input").press("Enter")
        else:
            self.page.locator("#send-button").click()
        wait_for(self.page, lambda: len(self.requests) > count, "No POST /chat was sent")
        assert len(self.requests) == count + 1, "A single submit sent multiple requests"
        assert self.payload() == {"message": message, "language": language or None}, \
            f"Wrong /chat payload: {self.payload()!r}"

    def release(self, route, data):
        try:
            route.fulfill(content_type="application/json", body=json.dumps(data))
        except PlaywrightError:
            # Chromium may already have disposed of a genuinely aborted route.
            if route.request not in self.failed_requests or "ABORTED" not in (route.request.failure or ""):
                raise
        self.pending.remove(route)

    def audit(self):
        # Let binding/console/request callbacks drain before checking them.
        self.page.wait_for_timeout(40)
        unexpected_console = []
        for text, url in self.console:
            resource_failure = (urlsplit(url).path == "/chat"
                                and text.startswith("Failed to load resource:"))
            transport_failure = bool(re.fullmatch(
                r"(?:TypeError: )?Failed to fetch|NetworkError:.*|(?:Error: )?HTTP 500", text))
            if self.expected_api_failures and (resource_failure or transport_failure):
                self.ignored_console += 1
            else:
                unexpected_console.append(f"{text} ({url})")
        problems = []
        if self.errors:
            problems.append(f"Browser errors: {self.errors}")
        if unexpected_console:
            problems.append(f"Unexpected console errors: {unexpected_console}")
        if self.violations:
            problems.append(f"Forbidden API use: {sorted(set(self.violations))}")
        if self.unexpected:
            problems.append(f"Blocked/unexpected requests: {self.unexpected}")
        if self.responses or self.pending:
            problems.append("Unused API responses or unreleased pending routes")
        assert not problems, "\n".join(problems)


def idle(page):
    expect(page.locator("#typing-indicator")).to_be_hidden()
    expect(page.locator("#typing-indicator[hidden]")).to_have_count(1)


def details_for(article):
    details = article.locator("details.translation-details")
    expect(details).to_have_count(1)
    expect(details.locator("summary")).to_have_text("Show translation details")
    if details.get_attribute("open") is None:
        details.locator("summary").click()
    return details


def assistant(page, text, language=None):
    article = page.locator(ASSISTANT).last
    expect(article.locator(".message-text")).to_have_text(text, use_inner_text=False)
    badge = article.locator(".language-badge")
    expect(badge).to_be_visible()
    expect(badge).to_have_text(re.compile(r"\S"))
    if language:
        names = next(row[1] for row in LANGUAGES if row[0] == language)
        expect(badge).to_contain_text(re.compile(rf"(?:\b{language}\b|{names})", re.I))
    details = details_for(article)
    assert not re.search(r"\b(?:null|undefined|NaN)\b|\[object Object\]", details.inner_text()), \
        "Missing metadata leaked raw JavaScript values"
    idle(page)
    return details


def error_state(page):
    expect(page.locator(ERROR)).to_have_count(1)
    expect(page.locator(ERROR + " .message-text")).to_have_text(re.compile(r"\S"))
    expect(page.locator(ERROR + " button.retry-button")).to_be_visible()
    expect(page.locator(ASSISTANT)).to_have_count(0)
    idle(page)


def check_shell(f):
    page = f.page
    required = ["select#language-select", "textarea#message-input", "form#chat-form",
                "#chat-form button#send-button[type=submit]", "button#theme-toggle",
                "button#clear-chat", "#welcome", "#welcome-title",
                "#suggestions .prompt-chip", '#messages[role="log"]', "#typing-indicator"]
    missing = [selector for selector in required if not page.locator(selector).count()]
    if missing:
        raise MissingContract(f"Frontend contract selectors missing: {missing}")
    assert {"/static/css/style.css", "/static/js/app.js"} <= f.assets, \
        f"Expected no-build assets were not loaded: {sorted(f.assets)}"
    options = page.locator("#language-select option").evaluate_all("els => els.map(e => e.value)")
    assert sorted(options) == sorted([""] + [row[0] for row in LANGUAGES]), options
    expect(page.locator("#language-select")).to_have_value("")
    expect(page.locator("html")).to_have_attribute("data-theme", "system")
    expect(page.locator("#welcome")).to_be_visible()
    expect(page.locator("#welcome-title")).to_have_text(re.compile(r"\S"))
    expect(page.locator("#messages article.message")).to_have_count(0)
    expect(page.locator("#send-button")).to_be_disabled()
    idle(page)
    for selector in ("#message-input", "#language-select", "#send-button", "#theme-toggle", "#clear-chat"):
        expect(page.locator(selector)).to_have_accessible_name(re.compile(r"\S"))

    skip = page.get_by_role("link", name=re.compile(r"skip", re.I))
    expect(skip).to_have_count(1)
    for _ in range(25):
        page.keyboard.press("Tab")
        if skip.evaluate("el => el === document.activeElement"):
            break
    expect(skip).to_be_focused()
    expect(skip).to_be_visible()
    target = unquote(urlsplit(skip.get_attribute("href")).fragment)
    assert target, "Skip link must name a page target"
    skip.press("Enter")
    page.wait_for_function("id => { const target = document.getElementById(id); "
                           "return target && target.contains(document.activeElement); }", arg=target)
    page.locator("#suggestions .prompt-chip").first.click()
    expect(page.locator("#message-input")).to_be_focused()
    assert page.locator("#message-input").input_value().strip(), "Suggestion did not fill a draft"
    expect(page.locator("#send-button")).to_be_enabled()
    expect(page.locator("article.message")).to_have_count(0)
    assert not f.requests, "Suggestion sent a message instead of filling the draft"


def check_language(f, row):
    code, _names, message, response = row
    f.enqueue(reply(response, code))
    f.send(message, code)
    expect(f.page.locator(USER + " .message-text")).to_have_text(message)
    details = assistant(f.page, response, code)
    expect(details).to_contain_text(re.compile(r"83(?:\.0+)?\s*%|0\.83\b"))
    expect(details).to_contain_text("library")
    expect(f.page.locator("#welcome")).to_be_hidden()
    expect(f.page.locator("#message-input")).to_have_value("")
    expect(f.page.locator("#send-button")).to_be_disabled()
    expect(f.page.locator(USER)).to_have_count(1)
    expect(f.page.locator(ASSISTANT)).to_have_count(1)


def check_autodetect(f):
    f.enqueue(reply("ਇਹ ਪੰਜਾਬੀ ਜਵਾਬ ਹੈ।", "pa"))
    f.send("ਮੈਨੂੰ ਲਾਇਬ੍ਰੇਰੀ ਬਾਰੇ ਦੱਸੋ", enter=True)
    assistant(f.page, "ਇਹ ਪੰਜਾਬੀ ਜਵਾਬ ਹੈ।", "pa")
    assert f.payload()["language"] is None, "Autodetection must send JSON null"


def check_metadata(f, mode):
    text = "Metadata should never prevent a valid reply."
    if mode == "null":
        data = reply(text, None, None)
        data.update(intent=None, language_meta=None)
    else:
        data = {"reply": text, "lang": "hi", "intent": "library", "confidence": 0.99}
        if mode == "nested":
            data["language_meta"] = {"confidence": 0.72}
        elif mode == "zero":
            data["language_meta"] = {"confidence": 0}
        elif mode == "null-nested":
            data["language_meta"] = {"confidence": None}
    f.enqueue(data)
    f.send("Check metadata")
    details = assistant(f.page, text, "hi" if mode != "null" else None)
    if mode == "nested":
        expect(details).to_contain_text(re.compile(r"72(?:\.0+)?\s*%|0\.72\b"))
    elif mode == "zero":
        expect(details).to_contain_text(re.compile(r"\b0(?:\.0+)?\s*%|confidence\s*:?\s*0\b", re.I))
    # A separately labelled intent/classifier confidence is fine. An unqualified
    # or detection confidence must not reuse Flask's top-level intent score.
    text = details.inner_text()
    for match in re.finditer(
            r"(?:(intent|classifier|detection|language)\s+)?confidence\s*:?\s*"
            r"(?:99(?:\.0+)?\s*%|0\.99\b)", text, re.I):
        assert (match.group(1) or "").lower() in ("intent", "classifier"), \
            f"Legacy classifier confidence shown as detection confidence: {text!r}"
    assert not re.search(r"\b(?:null|undefined|NaN)\b|\[object Object\]",
                         f.page.locator(ASSISTANT).inner_text()), "Unsafe null metadata display"


def check_literal_text(f):
    user = '<img src=x onerror="window.__injected=1"> user <b>literal</b> & "quoted"'
    response = '<img src=x onerror="window.__injected=2"> reply <script>window.__injected=3</script>'
    f.enqueue(reply(response, "en"))
    f.send(user)
    expect(f.page.locator(USER + " .message-text")).to_have_text(user, use_inner_text=False)
    assistant(f.page, response, "en")
    expect(f.page.locator("article.message .message-text > *")).to_have_count(0)
    expect(f.page.locator("article.message img, article.message script, article.message [onerror]")).to_have_count(0)
    assert f.page.evaluate("window.__injected === undefined"), "Payload executed as markup"


def check_invalid(f, data=None, raw=None):
    if raw is None:
        f.enqueue(data)
    else:
        f.enqueue(mode="raw", body=raw)
    f.send("Reject an invalid response")
    error_state(f.page)
    expect(f.page.locator(USER)).to_have_count(1)
    text = f.page.locator(ERROR + " .message-text").inner_text()
    assert not re.search(r"\b(?:undefined|NaN)\b|\[object Object\]|<img|<html", text), text


def check_retry(f, mode):
    if mode == "network":
        f.enqueue(mode="network")
    else:
        f.enqueue({"error": '<img src=x onerror="window.__injected=1">'}, status=500)
    f.send("Original retry payload", "hi")
    error_state(f.page)
    original = f.payload()
    f.page.locator("#language-select").select_option("de")
    f.page.locator("#message-input").fill("An unrelated unsent draft")
    f.enqueue(reply("ਮੁੜ ਕੋਸ਼ਿਸ਼ ਸਫਲ ਹੋਈ।", "pa"))
    f.page.locator(ERROR + " button.retry-button").click()
    wait_for(f.page, lambda: len(f.requests) == 2, "Retry did not send exactly one request")
    assert f.payload() == original, f"Retry mutated the original payload: {f.payload()!r}"
    assistant(f.page, "ਮੁੜ ਕੋਸ਼ਿਸ਼ ਸਫਲ ਹੋਈ।", "pa")
    expect(f.page.locator(USER)).to_have_count(1)
    expect(f.page.locator(USER + " .message-text")).to_have_text("Original retry payload")
    expect(f.page.locator(ASSISTANT)).to_have_count(1)
    expect(f.page.locator("article.message img, article.message [onerror]")).to_have_count(0)
    assert f.page.evaluate("window.__injected === undefined"), "Server error executed markup"
    assert len(f.requests) == 2, "Retry submitted more than once"


def check_composer(f):
    page = f.page
    field, send = page.locator("#message-input"), page.locator("#send-button")
    for blank in ("", "   \n  "):
        field.fill(blank)
        expect(send).to_be_disabled()
        field.press("Enter")
    field.fill("")
    initial_height = field.bounding_box()["height"]
    field.fill("One\nTwo\nThree\nFour\nFive\nSix")
    wait_for(page, lambda: field.bounding_box()["height"] > initial_height + 5,
             "Textarea did not grow for multiline input")
    field.fill("")
    wait_for(page, lambda: field.bounding_box()["height"] <= initial_height + 2,
             "Textarea did not shrink after clearing the draft")
    field.fill("First line")
    field.press("End")
    field.press("Shift+Enter")
    field.press("End")
    field.press_sequentially("Second line")
    expect(field).to_have_value("First line\nSecond line")
    for event in ({"isComposing": True}, {"keyCode": 229, "which": 229}):
        field.dispatch_event("keydown", {"key": "Enter", "code": "Enter", "bubbles": True,
                                         "cancelable": True, **event})
        page.wait_for_timeout(80)
        assert not f.requests, f"Blank, Shift+Enter or IME Enter submitted: {event}"
        expect(field).to_have_value("First line\nSecond line")
    f.enqueue(reply("Keyboard submit worked."))
    field.press("Enter")
    assistant(page, "Keyboard submit worked.", "en")
    assert len(f.requests) == 1, "Ordinary Enter must submit once"
    assert f.payload() == {"message": "First line\nSecond line", "language": None}


def check_clear_pending(f):
    f.enqueue(mode="hold")
    f.send("Old conversation")
    wait_for(f.page, lambda: bool(f.pending), "Chat request was not held")
    old_route = f.pending[0]
    expect(f.page.locator("#typing-indicator")).to_be_visible()
    expect(f.page.locator("#typing-indicator[hidden]")).to_have_count(0)
    f.page.locator("#clear-chat").click()
    expect(f.page.locator("article.message")).to_have_count(0, timeout=500)
    expect(f.page.locator("#welcome")).to_be_visible(timeout=500)
    expect(f.page.locator("#message-input")).to_have_value("")
    expect(f.page.locator("#send-button")).to_be_disabled()
    idle(f.page)
    # A new turn succeeds even while the obsolete server response is held.
    f.enqueue(reply("Only the new conversation survives."))
    f.send("New conversation")
    assistant(f.page, "Only the new conversation survives.", "en")
    f.release(old_route, reply("STALE RESPONSE MUST NEVER APPEAR"))
    f.page.wait_for_timeout(150)
    expect(f.page.locator(USER)).to_have_count(1)
    expect(f.page.locator(ASSISTANT)).to_have_count(1)
    expect(f.page.locator(ERROR)).to_have_count(0)
    expect(f.page.locator("#messages")).not_to_contain_text("STALE RESPONSE")
    expect(f.page.locator(USER + " .message-text")).to_have_text("New conversation")
    wait_for(f.page, lambda: old_route.request in f.failed_requests,
             "Clear hid the old turn but did not abort its fetch")
    assert "ABORTED" in (old_route.request.failure or ""), old_route.request.failure
    idle(f.page)
    f.page.locator("#clear-chat").click()
    expect(f.page.locator("article.message")).to_have_count(0)
    expect(f.page.locator("#welcome")).to_be_visible()


def check_reload(f):
    f.enqueue(reply("Ephemeral answer."))
    f.send("Ephemeral question", "fr")
    assistant(f.page, "Ephemeral answer.", "en")
    f.page.locator("#message-input").fill("Ephemeral draft")
    f.page.reload(wait_until="load")
    expect(f.page.locator("#welcome")).to_be_visible()
    expect(f.page.locator("article.message")).to_have_count(0)
    expect(f.page.locator("#message-input")).to_have_value("")
    expect(f.page.locator("#send-button")).to_be_disabled()
    assert len(f.requests) == 1, "Reload replayed a previous chat request"
    idle(f.page)


def check_localized_suggestions(f):
    previous = set()
    for code, _name, _message, _reply in LANGUAGES:
        f.page.locator("#language-select").select_option(code)
        chips = f.page.locator("#suggestions .prompt-chip")
        expect(chips).to_have_count(4)
        assert chips.evaluate_all("els => els.every(el => el.lang === els[0].lang)")
        expect(chips.first).to_have_attribute("lang", code)
        text = chips.first.inner_text().replace("↗", "").strip()
        assert text not in previous, "Language change reused the same suggested prompt"
        previous.add(text)
        chips.first.click()
        expect(f.page.locator("#message-input")).to_have_value(text)
        expect(f.page.locator("#message-input")).to_be_focused()
    assert not f.requests, "Localized suggestion sent without confirmation"


def check_rtl_and_scroll(f):
    text = "مرحباً، أين المكتبة؟"
    response = "المكتبة مفتوحة اليوم."
    for index in range(8):
        f.enqueue(reply(response + "\n" + "نص طويل للتمرير. " * 20, "ar"))
        f.send(text + str(index))
        expect(f.page.locator(ASSISTANT)).to_have_count(index + 1)
    for role in (USER, ASSISTANT):
        article = f.page.locator(role).last
        expect(article.locator(".bubble")).to_have_attribute("dir", "auto")
        assert article.locator(".message-text").evaluate("el => getComputedStyle(el).direction") == "rtl"
        assert article.locator("time").get_attribute("datetime")
    f.page.wait_for_function("() => { const s = document.querySelector('#chat-scroll'); "
                            "return Math.abs(s.scrollHeight - s.scrollTop - s.clientHeight) < 4; }")
    no_overflow(f.page)


def check_timeout(f):
    f.page.clock.install()
    f.enqueue(mode="hold")
    f.send("A reply that never arrives")
    wait_for(f.page, lambda: bool(f.pending), "Timeout fixture was not held")
    route = f.pending[0]
    f.page.clock.fast_forward(46000)
    error_state(f.page)
    expect(f.page.locator(ERROR)).to_contain_text("longer than expected")
    f.release(route, reply("STALE TIMEOUT REPLY"))
    f.enqueue(reply("Recovered from timeout."))
    f.page.locator(".retry-button").click()
    assistant(f.page, "Recovered from timeout.", "en")
    expect(f.page.locator(USER)).to_have_count(1)
    expect(f.page.locator("#messages")).not_to_contain_text("STALE TIMEOUT REPLY")


def check_composition_lifecycle(f):
    field = f.page.locator("#message-input")
    field.fill("कैंपस")
    field.dispatch_event("compositionstart")
    expect(f.page.locator("#send-button")).to_be_disabled()
    field.press("Enter")
    f.page.wait_for_timeout(80)
    assert not f.requests, "Active composition submitted a message"
    field.dispatch_event("compositionend")
    f.enqueue(reply("Composition is complete.", "hi"))
    field.press("Enter")
    assistant(f.page, "Composition is complete.", "hi")


PALETTE = """() => [document.documentElement, document.body,
  document.querySelector('#message-input')].map(el => {
    const s = getComputedStyle(el); return [s.backgroundColor, s.color];
  })"""


def palette(page):
    return page.evaluate(PALETTE)


def expect_palette(page, expected):
    page.wait_for_function(f"expected => JSON.stringify(({PALETTE})()) === JSON.stringify(expected)",
                           arg=expected)


def check_theme(f):
    page = f.page
    html, toggle = page.locator("html"), page.locator("#theme-toggle")
    expect(html).to_have_attribute("data-theme", "system")
    light = palette(page)
    page.emulate_media(color_scheme="dark")
    page.wait_for_function(f"before => JSON.stringify(({PALETTE})()) !== JSON.stringify(before)", arg=light)
    dark = palette(page)
    expect(html).to_have_attribute("data-theme", "system")
    toggle.click()
    expect(html).to_have_attribute("data-theme", "light")
    expect_palette(page, light)
    toggle.click()
    expect(html).to_have_attribute("data-theme", "dark")
    expect_palette(page, dark)
    page.emulate_media(color_scheme="light")
    expect_palette(page, dark)
    toggle.click()
    expect(html).to_have_attribute("data-theme", "system")
    expect_palette(page, light)


def no_overflow(page):
    problems = page.evaluate("""() => {
      const issues = [], width = innerWidth;
      for (const el of [document.documentElement, document.body,
          ...document.querySelectorAll('#messages, .message-text, .translation-details')]) {
        if (el.getClientRects().length && el.scrollWidth > el.clientWidth + 1)
          issues.push(`${el.id || el.className || el.tagName}: ${el.scrollWidth} > ${el.clientWidth}`);
      }
      for (const selector of ['#message-input', '#send-button', '#language-select', '#theme-toggle', '#clear-chat']) {
        const r = document.querySelector(selector).getBoundingClientRect();
        if (r.left < -1 || r.right > width + 1 || r.top < -1 || r.bottom > innerHeight + 1)
          issues.push(`${selector} outside ${width}x${innerHeight} viewport`);
      }
      return issues;
    }""")
    assert not problems, f"Layout overflow/clipped controls: {problems}"


def reduced_motion(page):
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    problems = page.evaluate("""() => {
      const issues = [];
      const long = value => value.split(',').some(s => parseFloat(s) > 0.01);
      for (const el of document.querySelectorAll('*')) {
        if (!el.getClientRects().length) continue;
        for (const pseudo of [null, '::before', '::after']) {
          const s = getComputedStyle(el, pseudo);
          if ((s.animationName !== 'none' && long(s.animationDuration)) ||
              (s.transitionProperty !== 'none' && long(s.transitionDuration)))
            issues.push(`${el.id || el.className || el.tagName}${pseudo || ''}`);
        }
        if (getComputedStyle(el).scrollBehavior === 'smooth') issues.push('smooth scrolling');
      }
      return issues.slice(0, 12);
    }""")
    assert not problems, f"Motion remains enabled under prefers-reduced-motion: {problems}"


def check_layout(f, theme):
    for _ in range(1 if theme == "light" else 2):
        f.page.locator("#theme-toggle").click()
    expect(f.page.locator("html")).to_have_attribute("data-theme", theme)
    no_overflow(f.page)
    f.enqueue(mode="hold")
    f.send("LongUnbrokenUserToken" * 15)
    wait_for(f.page, lambda: bool(f.pending), "No pending layout fixture")
    expect(f.page.locator("#typing-indicator")).to_be_visible()
    reduced_motion(f.page)
    no_overflow(f.page)
    response = "LongUnbrokenReplyToken" * 25 + " हिन्दी ਪੰਜਾਬੀ ¿Español? Français Deutsch"
    f.release(f.pending[0], reply(response, "hi"))
    assistant(f.page, response, "hi")
    no_overflow(f.page)
    reduced_motion(f.page)


def main():
    missing = [name for name in ("templates/index.html", "static/css/style.css", "static/js/app.js")
               if not (ROOT / name).is_file()]
    if missing:
        print(f"FAIL frontend preflight: missing {', '.join(missing)}", file=sys.stderr)
        print("0 browser cases run; the no-build frontend files must exist first.")
        return 1

    cases = [("shell contract, accessible labels, keyboard skip link and draft-only suggestions", check_shell, 1440)]
    cases += [(f"selected {row[0]}: exact JSON payload, Unicode reply, badge and translation details",
               partial(check_language, row=row), 1440)
              for row in LANGUAGES]
    cases.append(("autodetect sends null; Enter sends once and detected Punjabi badge renders", check_autodetect, 1440))
    cases += [(f"metadata {mode}: safe values and correct detection-confidence source",
               partial(check_metadata, mode=mode), 1440)
              for mode in ("null", "nested", "zero", "missing-nested", "null-nested")]
    cases.append(("hostile user/reply HTML remains literal text without injected elements", check_literal_text, 1440))
    invalid = [("null", None), ("array", []), ("string", "not an object"), ("missing reply", {}),
               ("null reply", {"reply": None}), ("object reply", {"reply": {"unsafe": "value"}}),
               ("numeric reply", {"reply": 42}), ("empty reply", {"reply": ""}),
               ("whitespace reply", {"reply": " \n "})]
    cases += [(f"invalid response ({name}) produces a recoverable error",
               partial(check_invalid, data=data), 1440) for name, data in invalid]
    cases.append(("invalid JSON/HTML response produces a safe recoverable error",
                  partial(check_invalid, raw='<html><img src=x onerror="window.__injected=1"></html>'), 1440))
    cases += [(f"{mode} failure: retry preserves original payload after draft/language changes, no duplicate user",
               partial(check_retry, mode=mode), 1440) for mode in ("network", "HTTP 500")]
    cases += [("composer: empty disabled, auto-grow/shrink, Shift+Enter, IME composing/keyCode229, normal Enter",
               check_composer, 1440),
              ("clear immediately resets, aborts pending fetch and excludes stale replies from a new conversation",
               check_clear_pending, 1440),
              ("reload erases conversation and draft without replay or browser storage", check_reload, 1440),
               ("system color scheme responds live; manual system/light/dark cycle overrides it", check_theme, 1440)]
    cases += [("all six languages have distinct draft-only localized suggestions", check_localized_suggestions, 1440),
              ("RTL text, semantic timestamps and auto-scroll across long conversation", check_rtl_and_scroll, 360),
              ("timeout aborts request and retry recovers without a duplicate turn", check_timeout, 1440),
              ("compositionstart/end lifecycle prevents premature submission", check_composition_lifecycle, 1440)]
    cases += [(f"{width}px {theme}: welcome/pending/reply layout, long Unicode text, reduced motion, no overflow",
               partial(check_layout, theme=theme), width)
              for width in (360, 768, 1440) for theme in ("light", "dark")]

    passed = failed = attempted = ignored_console = 0
    expect.set_options(timeout=TIMEOUT)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            print(f"Offline frontend checks — Chromium {browser.version}", flush=True)
            try:
                for label, check, width in cases:
                    fixture = Frontend(browser, width)
                    attempted += 1
                    failure = []
                    missing_contract = False
                    try:
                        fixture.open()
                        check(fixture)
                    except Exception as error:
                        failure.append(str(error) or type(error).__name__)
                        missing_contract = isinstance(error, MissingContract)
                    try:
                        fixture.audit()
                    except Exception as error:
                        failure.append(str(error) or type(error).__name__)
                    finally:
                        ignored_console += fixture.ignored_console
                        fixture.context.close()
                    if failure:
                        failed += 1
                        print(f"FAIL {label}\n  " + "\n  ".join(failure), flush=True)
                    else:
                        passed += 1
                        print(f"PASS {label}", flush=True)
                    if missing_contract:
                        print("Remaining cases not run: fix the shell contract first.", flush=True)
                        break
            finally:
                browser.close()
    except Exception as error:
        failed += 1
        print(f"FAIL browser/test harness: {error}", file=sys.stderr)
    print(f"\n{passed} passed; {failed} failed; {len(cases) - attempted} "
          f"not run; {ignored_console} expected API console errors ignored.")
    print("All executed cases also audit page errors, unexpected network, storage and innerHTML use.")
    print("Scope: Chromium with mocked API; no live Flask/model, real OS IME, other browsers, "
          "visual comparison or full accessibility audit.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
