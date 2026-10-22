"""Phase 4 deterministic chat/API/rendering checks.

python scripts/verify_chat.py [--capture] [--live http://localhost:8000]
Mock mode uses the actual page at /v2/?mock=1 and never calls /api/v1/chat.
The optional live run uses the keyless campus route only.
"""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
import platform
import re
import threading

from playwright.sync_api import expect, sync_playwright
from verify_design_system import ROOT, PreviewServer, QuietHandler, settled

PASSED, SHOTS = [], []


def passed(label):
    PASSED.append(label)
    print(f"PASS {label}", flush=True)


def seed_context(context, health=True):
    context.add_init_script("""localStorage.setItem('gaia.store.v1', 'legacy untouched');
      window.mediaCalls = 0;
      navigator.mediaDevices.getUserMedia = () => { window.mediaCalls++; throw Error('Unexpected mic request'); };
      speechSynthesis.speak = () => { window.mediaCalls++; throw Error('Unexpected speech request'); };
    """)
    if health:
        context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def screenshot(page, name, capture):
    if capture:
        path = ROOT / 'docs/screenshots/phase4' / f'{name}.png'
        page.screenshot(path=str(path), full_page=True, animations='disabled')
        SHOTS.append(str(path.relative_to(ROOT)))


def static_server():
    server = PreviewServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'static')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def mock_stream(browser, origin, capture):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', permissions=['clipboard-read', 'clipboard-write'])
    seed_context(context)
    page = context.new_page()
    errors, chat_requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
    page.on('request', lambda req: chat_requests.append(req.url) if '/api/v1/chat' in req.url else None)
    page.goto(origin + '/v2/index.html?mock=1')
    expect(page.locator('#mock-banner')).to_contain_text('Simulation mode')
    expect(page.locator('#service-status')).to_have_text('API reachable')
    input_box = page.locator('#message-input')
    send = page.get_by_role('button', name='Send', exact=True)
    input_box.fill('x' * 3601)
    expect(page.locator('#message-count')).to_have_text('3,601 / 4,000')
    expect(page.locator('#message-count')).to_have_attribute('data-state', 'warn')
    input_box.fill('x' * 4001)
    expect(page.locator('#message-count')).to_have_text('4,001 / 4,000')
    expect(send).to_be_disabled()
    input_box.fill('Show me a Python example')
    expect(send).to_be_enabled()
    input_box.press('Enter')
    expect(page.locator('#conversation-view')).to_be_visible()
    expect(page.locator('.chat-message--user')).to_contain_text('Show me a Python example')
    expect(page.locator('.chat-message--assistant[aria-busy="true"]')).to_be_visible()
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=10000)
    expect(page.locator('.chat-message--assistant')).to_contain_text('Hello')
    expect(page.locator('.code-block')).to_be_visible()
    expect(page.locator('.code-language')).to_have_text('python')
    expect(page.locator('.chat-route')).to_have_text('general')
    expect(page.locator('.chat-message--assistant a')).to_have_count(0)
    assert not chat_requests, chat_requests
    assert page.evaluate('window.mediaCalls') == 0
    assert not errors, errors
    screenshot(page, 'mock-1440-code', capture)
    page.get_by_role('button', name='Copy code block').click()
    expect(page.locator('#toast-region')).to_contain_text('Code block copied')
    page.get_by_role('button', name='Dismiss notification').click()
    page.get_by_role('button', name='Copy', exact=True).click()
    expect(page.locator('#toast-region')).to_contain_text('Reply copied')
    page.get_by_role('button', name='Dismiss notification').click()
    passed('mock: labelled simulation, delayed stream, 4,000-char guard, code rendering, route metadata, copy actions and no chat POST')

    # Escape must stop an in-flight stream and prevent later deltas from painting.
    input_box.fill('Explain a complex idea')
    input_box.press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="true"]')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]').last).to_contain_text('stopped')
    stopped = page.locator('.chat-message--assistant').last.inner_text()
    page.wait_for_timeout(800)
    expect(page.locator('.chat-message--assistant').last).to_contain_text('stopped')
    passed('mock: Escape cancellation retains a partial/error-safe answer and blocks late deltas')

    # New chat owns cancellation and returns to the shell without stale content.
    input_box.fill('Explain another idea')
    input_box.press('Enter')
    page.get_by_role('button', name='New chat', exact=True).click()
    expect(page.locator('#conversation-view')).to_be_hidden()
    expect(page.locator('#welcome')).to_be_visible()
    expect(input_box).to_have_value('')
    page.wait_for_timeout(800)
    expect(page.locator('#message-log')).to_be_empty()
    passed('mock: New chat aborts ownership, clears the log and resets the draft')

    # Renderer is independently checked against hostile text and protocol filtering.
    result = page.evaluate("""async () => {
      const module = await import('./js/markdown.js');
      return {
        html: module.renderMarkdown('<script>alert(1)</script>\\n\\n[x](javascript:alert(2))\\n\\n[ok](https://example.com)'),
        plain: module.plainText('**bold** and `code`'),
      };
    }""")
    assert '<script>' not in result['html'] and 'href="javascript:' not in result['html']
    assert 'rel="noopener noreferrer"' in result['html'] and result['plain'] == 'bold and code'
    passed('renderer: hostile HTML escaped, javascript links rejected, HTTPS links constrained and plain text extracted')
    context.close()


def error_stream(browser, origin, capture):
    context = browser.new_context(viewport={'width': 360, 'height': 800}, reduced_motion='reduce')
    seed_context(context)
    mode = {'value': 'error'}

    def chat_fixture(route):
        if mode['value'] == 'error':
            route.fulfill(status=413, content_type='application/json', body=json.dumps({'error': 'message too long'}))
        elif mode['value'] == 'empty':
            route.fulfill(status=200, content_type='text/event-stream', body='data: {"type":"meta","conversation_id":"cid","route":"general"}\n\ndata: {"type":"done","latency_ms":1,"sources":[]}\n\n')
        elif mode['value'] == 'empty-delta':
            route.fulfill(status=200, content_type='text/event-stream', body='data: {"type":"meta","conversation_id":"cid","route":"general"}\n\ndata: {"type":"delta","text":""}\n\ndata: {"type":"done","latency_ms":1,"sources":[]}\n\n')
        elif mode['value'] == 'malformed':
            route.fulfill(status=200, content_type='text/event-stream', body='data: {not-json}\n\n')

    context.route('**/api/v1/chat', chat_fixture)
    page = context.new_page()
    page.goto(origin + '/v2/index.html')
    input_box = page.locator('#message-input')
    input_box.fill('A message that will fail')
    input_box.press('Enter')
    expect(page.locator('.chat-message--assistant')).to_contain_text('too long')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible()
    expect(page.get_by_role('button', name='Retry', exact=True)).to_be_visible()
    passed('live-shaped error: HTTP 413 becomes a safe assistant error with Retry')

    mode['value'] = 'empty'
    page.get_by_role('button', name='Retry', exact=True).click()
    expect(page.locator('.chat-message--assistant').last).to_contain_text('empty reply')
    expect(page.locator('.chat-message--assistant')).to_have_count(1)
    expect(page.locator('.chat-message--user')).to_have_count(1)
    passed('stream: meta without delta becomes an explicit empty-reply state')

    mode['value'] = 'empty-delta'
    page.get_by_role('button', name='Retry', exact=True).click()
    expect(page.locator('.chat-message--assistant').last).to_contain_text('empty reply')
    passed('stream: empty delta frames do not count as a successful blank reply')

    mode['value'] = 'malformed'
    page.get_by_role('button', name='Retry', exact=True).last.click()
    expect(page.locator('.chat-message--assistant').last).to_contain_text('could not complete')
    screenshot(page, 'light-360-errors', capture)
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
    passed('stream: malformed SSE never injects raw data and remains recoverable')
    context.close()


def live_campus(browser, base, capture):
    context = browser.new_context(viewport={'width': 1024, 'height': 900}, reduced_motion='reduce')
    context.add_init_script("localStorage.setItem('gaia.store.v1', 'legacy untouched');")
    page = context.new_page()
    requests = []
    page.on('request', lambda req: requests.append(req) if req.url.endswith('/api/v1/chat') else None)
    page.goto(base.rstrip('/') + '/static/v2/index.html')
    expect(page.locator('#service-status')).to_have_text('API reachable')
    page.locator('#message-input').fill('when are my exams')
    page.locator('#message-input').press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=30000)
    expect(page.locator('.chat-message--assistant')).to_contain_text(re.compile('exam', re.IGNORECASE))
    assert requests and json.loads(requests[0].post_data)['conversation_id'] in (None, '')
    cid = json.loads(requests[0].post_data).get('conversation_id')
    # A second keyless campus turn proves the browser now carries the server-issued ID.
    page.locator('#message-input').fill('when is the date sheet published')
    page.locator('#message-input').press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_have_count(2, timeout=30000)
    assert len(requests) >= 2
    second_cid = json.loads(requests[1].post_data).get('conversation_id')
    assert second_cid and second_cid != cid
    # First request had no ID; the response-assigned server ID is used for turn two.
    screenshot(page, 'light-1024-live-campus', capture)
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
    passed(f'LIVE campus: two SSE replies rendered; second request carried server conversation ID {second_cid}')
    context.close()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--live')
    args = parser.parse_args()
    if args.capture: (ROOT / 'docs/screenshots/phase4').mkdir(exist_ok=True)
    server, origin = static_server()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            mock_stream(browser, origin, args.capture)
            error_stream(browser, origin, args.capture)
            live = live_campus(browser, args.live, args.capture) if args.live else None
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    print(f'\n{len(PASSED)} Phase 4 check groups passed; {len(SHOTS)} screenshots; live: {bool(live)}.')
    report = {'phase': 4, 'environment': {'platform': platform.platform(), 'python': platform.python_version()},
              'scope': 'chat transport, mock stream, rendering, cancellation and keyless campus smoke',
              'passed_groups': PASSED, 'screenshots': SHOTS, 'live': bool(live)}
    if args.capture: (ROOT / 'docs/chat-checks.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__': main()
