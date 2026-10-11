"""Frontend startup diagnosis; does not edit sources or replace browser assertions.

Run from the project root with FastAPI on :8000:
    python scripts/diagnose_frontend_startup.py
Requires the already-approved Playwright and httpx test tools.
"""

import argparse
import json
import subprocess

import httpx
from playwright.sync_api import sync_playwright


def report(label, value):
    print(f"{label}: {json.dumps(value, ensure_ascii=False)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    try:
        syntax = subprocess.run(
            ["node", "--check", "static/js/markdown.js"],
            capture_output=True, text=True, check=False,
        )
        report("JavaScript syntax exit", syntax.returncode)
        print(syntax.stderr.strip(), flush=True)
    except FileNotFoundError:
        report("Node syntax check", "Not run: Node is unavailable. Continuing with Chromium evidence.")

    with httpx.Client(timeout=30) as client:
        health = client.get(base + "/api/v1/health")
        report("Health", {"http_status": health.status_code, **health.json()})
        asset = client.get(base + "/static/js/markdown.js")
        report("Markdown asset", {"status": asset.status_code, "bytes": len(asset.content)})
        cid = client.post(base + "/api/v1/conversations").json()["conversation_id"]
        try:
            response = client.post(base + "/api/v1/chat", json={
                "message": "when are my exams", "conversation_id": cid,
            })
            frames = [json.loads(frame[5:].strip()) for frame in response.text.split("\n\n")
                      if frame.startswith("data:")]
            report("Direct campus request", {
                "status": response.status_code,
                "frame_types": [frame["type"] for frame in frames],
                "route": frames[0].get("route") if frames else None,
                "text": "".join(frame.get("text", "") for frame in frames),
                "errors": [frame for frame in frames if frame["type"] == "error"],
            })
        finally:
            report("Diagnostic conversation cleanup", client.delete(base + "/api/v1/chat/" + cid).json())

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url)
                if request.method == "POST" and "/api/v1/chat" in request.url else None)
        page.goto(base)
        page.wait_for_selector("#welcome.show")
        page.fill("#input", "when are my exams")
        page.press("#input", "Enter")
        page.wait_for_timeout(1500)
        report("Browser", browser.version)
        report("Page errors", errors)
        report("Chat POSTs after Enter", requests)
        report("DOM state", page.evaluate("""() => ({
            md: typeof window.md,
            esc: typeof window.esc,
            speechText: typeof window.speechText,
            suggestions: document.querySelectorAll('.welcome__card').length,
            allMessages: document.querySelectorAll('.msg').length,
            oldSelector: document.querySelectorAll('.msg.assistant .bubble').length,
            splitSelector: document.querySelectorAll('.msg--assistant .msg__bubble').length
        })"""))
        browser.close()


if __name__ == "__main__":
    main()
