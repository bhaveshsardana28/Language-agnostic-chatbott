"""Phase 3 shell regression checks, with explicit health-response test fixtures.

python scripts/verify_shell.py [--capture] [--live http://localhost:8000]
The offline battery serves only static/ on an ephemeral port. --live additionally
checks the actual health endpoint and rendered shell; no chat POST is made.
"""
import argparse
from functools import partial
import json
import platform
import threading

from playwright.sync_api import expect, sync_playwright
from verify_design_system import ROOT, KEY, QuietHandler, PreviewServer, settled

PASSED, SHOTS = [], []


def passed(label):
    PASSED.append(label)
    print(f"PASS {label}", flush=True)


def shot(page, name, capture):
    if capture:
        settled(page)
        path = ROOT / 'docs/screenshots/phase3' / f'{name}.png'
        page.screenshot(path=str(path), animations='disabled')
        SHOTS.append(str(path.relative_to(ROOT)))


def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal viewport overflow'
    dimensions = page.evaluate("""() => ({height:innerHeight, scroll:document.documentElement.scrollHeight,
      body:document.body.scrollHeight, active:document.activeElement.id,
      overflowing:[...document.body.children].map(e => ({tag:e.tagName, id:e.id, bottom:e.getBoundingClientRect().bottom}))
        .filter(e => e.bottom > innerHeight)})""")
    assert dimensions['scroll'] <= dimensions['height'], dimensions
    box = page.locator('#compose-region').bounding_box()
    size = page.viewport_size
    assert box['y'] >= 0 and abs(box['y'] + box['height'] - size['height']) < 2, box
    form = page.locator('#composer-form').bounding_box()
    main = page.locator('#main-content').bounding_box()
    assert form['x'] >= 0 and form['x'] + form['width'] <= size['width'] + 1
    assert main['height'] > 80 and main['y'] + main['height'] <= box['y'] + 1, (main, box)
    for control in page.get_by_role('button').all():
        if control.is_visible():
            assert control.get_attribute('aria-label') or control.inner_text().strip()
            assert control.bounding_box()['height'] >= 44, control


def trap(page, selector):
    page.locator(selector).locator('button:visible').first.focus()
    for key in ['Shift+Tab', *(['Tab'] * 12)]:
        page.keyboard.press(key)
        assert page.evaluate(f"document.activeElement.closest('{selector}') !== null"), (selector, key)


def context_setup(context):
    context.add_init_script("""if (!sessionStorage.getItem('seeded')) {
      localStorage.setItem('gaia.store.v1', 'legacy untouched'); sessionStorage.setItem('seeded', 'yes');
    }
    window.mediaCalls = 0;
    navigator.mediaDevices.getUserMedia = () => { window.mediaCalls++; throw Error('Unexpected mic request'); };
    speechSynthesis.speak = () => { window.mediaCalls++; throw Error('Unexpected speech request'); };
    """)
    context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def layout_and_interactions(browser, origin, capture):
    for theme in ('light', 'dark'):
        context = browser.new_context(color_scheme=theme, reduced_motion='no-preference')
        context_setup(context)
        page = context.new_page()
        errors, failed, requests = [], [], []
        page.on('pageerror', lambda error: (errors.append(str(error)), print(f'PAGE ERROR: {error}', flush=True)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.on('response', lambda res: failed.append(res.url) if res.status >= 400 else None)
        page.on('request', lambda req: requests.append((req.method, req.url)))
        for width, height in ((360, 800), (768, 900), (1024, 900), (1440, 1000)):
            page.set_viewport_size({'width': width, 'height': height})
            page.goto(origin + '/v2/index.html')
            try:
                expect(page.locator('#service-status')).to_have_text('API reachable')
            except AssertionError:
                print('Startup diagnostics:', page.evaluate("""() => ({hidden:document.hidden,
                  ready:document.readyState, online:navigator.onLine,
                  retry:document.querySelector('#health-retry').textContent,
                  icons:document.querySelectorAll('symbol').length,
                  resources:performance.getEntriesByType('resource').map(e => ({name:e.name,duration:e.duration}))})"""),
                      'requests:', requests, 'errors:', errors, flush=True)
                raise
            expect(page.locator('html')).to_have_attribute('data-theme', theme)
            expect(page.locator('[data-prompt]')).to_have_count(6)
            expect(page.get_by_role('button', name='Send', exact=True)).to_be_disabled()
            page.keyboard.press('Tab')
            expect(page.get_by_role('link', name='Skip to conversation')).to_be_focused()
            page.keyboard.press('Enter')
            expect(page.locator('#main-content')).to_be_focused()
            # Pause via the real accessible control for reproducible review captures.
            page.locator('#greeting-pause').click()
            settled(page)
            fits(page)
            shot(page, f'{theme}-{width}-welcome', capture)
            toggle = page.locator('#sidebar-toggle')
            if width < 1024:
                expect(page.locator('#app-sidebar')).to_be_hidden()
                toggle.click()
                expect(page.locator('#new-chat')).to_be_focused()
                expect(toggle).to_have_attribute('aria-expanded', 'true')
                trap(page, '#navigation-drawer')
                assert page.locator('#navigation-drawer').evaluate('e => e.scrollWidth <= e.clientWidth')
                shot(page, f'{theme}-{width}-navigation', capture)
                page.keyboard.press('Escape')
                expect(page.locator('#navigation-drawer')).to_be_hidden()
                expect(toggle).to_be_focused()
                toggle.click()
                page.mouse.click(width - 3, height / 2)
                expect(page.locator('#navigation-drawer')).to_be_hidden()
                expect(toggle).to_be_focused()
            else:
                expect(page.locator('#app-sidebar')).to_be_visible()
                toggle.click()
                expect(page.locator('html')).to_have_attribute('data-sidebar', 'collapsed')
                page.reload()
                expect(toggle).to_have_attribute('aria-expanded', 'false')
                assert page.locator('#sidebar-dock').bounding_box()['width'] == 76
                assert json.loads(page.evaluate(f"localStorage.getItem('{KEY}')"))['sideCollapsed'] is True
                if width == 1440:
                    shot(page, f'{theme}-{width}-collapsed', capture)
                toggle.click()
                expect(page.locator('html')).to_have_attribute('data-sidebar', 'expanded')
            passed(f'{theme}/{width}: viewport/docked composer, six prompts, labelled controls and responsive sidebar')

            for prompt in page.locator('[data-prompt]').all():
                text = prompt.get_attribute('data-prompt')
                prompt.click()
                expect(page.locator('#message-input')).to_have_value(text)
                expect(page.locator('#message-input')).to_be_focused()
                expect(page.get_by_role('button', name='Send', exact=True)).to_be_enabled()
                fits(page)
            assert page.evaluate('window.scrollY') == 0
            draft = page.locator('#message-input')
            draft.fill('Draft kept while I move around.')
            draft.press('Shift+Enter')
            assert draft.input_value().endswith('\n')
            draft.fill('line\n' * 30)
            assert draft.bounding_box()['height'] <= 200
            fits(page)
            draft.fill('Draft kept while I move around.')
            # A single sidebar node is reparented; opening settings closes nav first.
            if width < 1024:
                toggle.click()
            page.get_by_role('button', name='Appearance settings', exact=True).click()
            expect(page.locator('#navigation-drawer')).to_be_hidden()
            expect(page.locator('#settings-dialog')).to_be_visible()
            trap(page, '#settings-dialog')
            if width in (360, 1440):
                shot(page, f'{theme}-{width}-settings', capture)
            page.keyboard.press('Escape')
            expect(page.locator('#settings-dialog')).to_be_hidden()
            expect(draft).to_have_value('Draft kept while I move around.')
            if width < 1024:
                expect(toggle).to_be_focused()
                toggle.click()
            page.locator('#new-chat').click()
            expect(draft).to_have_value('')
            expect(draft).to_be_focused()
            expect(page.locator('#conversation-heading')).to_have_text('New conversation')
            page.get_by_role('button', name='Attach a document', exact=True).click()
            expect(page.locator('#documents-dialog')).to_be_visible()
            if width == 1440:
                shot(page, f'{theme}-{width}-documents', capture)
            page.keyboard.press('Escape')
            expect(page.get_by_role('button', name='Attach a document', exact=True)).to_be_focused()
            expect(page.locator('#voice-input-button')).to_be_visible()
            expect(page.locator('#voice-input-status')).to_contain_text('Voice input')
            assert page.evaluate('window.mediaCalls') == 0
            passed(f'{theme}/{width}: prompts/Shift+Enter edit, long draft fits, modal focus, New chat and future-feature entry points')

        # Resize with focus inside open navigation must clear top-layer/inert state.
        page.set_viewport_size({'width': 360, 'height': 800})
        page.locator('#sidebar-toggle').click()
        expect(page.locator('#new-chat')).to_be_focused()
        page.set_viewport_size({'width': 1440, 'height': 1000})
        expect(page.locator('#navigation-drawer')).to_be_hidden()
        expect(page.locator('#sidebar-toggle')).to_be_focused()
        expect(page.locator('#sidebar-dock #app-sidebar')).to_have_count(1)
        page.locator('#new-chat').focus()
        page.set_viewport_size({'width': 360, 'height': 800})
        expect(page.locator('#sidebar-toggle')).to_be_focused()
        expect(page.locator('#app-sidebar')).to_be_hidden()
        page.set_viewport_size({'width': 768, 'height': 450})
        fits(page)
        # Shared theme changes must retain the separately persisted sidebar choice.
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('#sidebar-toggle').click()
        page.locator('#theme-toggle').click()
        other = 'dark' if theme == 'light' else 'light'
        page.reload()
        expect(page.locator('html')).to_have_attribute('data-theme', other)
        expect(page.locator('html')).to_have_attribute('data-sidebar', 'collapsed')
        # In-app reduction is exercised on the actual shell as well as the component lab.
        page.get_by_role('button', name='Appearance settings', exact=True).click()
        page.locator('#reduce-motion').check()
        page.keyboard.press('Escape')
        expect(page.locator('#settings-dialog')).to_be_hidden()
        expect(page.locator('#greeting-pause')).to_be_disabled()
        page.reload()
        expect(page.locator('html')).to_have_attribute('data-motion', 'reduced')
        passed(f'{theme}: drawer resize cleanup/focus and short landscape viewport')
        passed(f'{theme}: shared appearance changes preserve sidebar state and in-app motion across reload')
        assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
        assert not errors and not failed, (errors, failed)
        assert all(method == 'GET' and (url.startswith(origin + '/v2/') or url == origin + '/api/v1/health')
                   for method, url in requests), requests
        passed(f'{theme}: no console/asset failures, only static + health GETs, legacy storage unchanged')
        context.close()


def lifecycle(browser, origin):
    context = browser.new_context(viewport={'width': 1024, 'height': 900})
    context_setup(context)
    page = context.new_page()
    page.goto(origin + '/v2/index.html')
    greeting = page.locator('#greeting')
    expect(greeting).to_have_attribute('lang', 'en')
    for lang in ('hi', 'pa', 'es', 'fr', 'de', 'it', 'en'):
        expect(greeting).to_have_attribute('lang', lang, timeout=7000)
        settled(page)
    passed('welcome: all seven greeting/script states cycle in order')
    page.locator('#greeting-pause').click()
    before = greeting.inner_text()
    page.wait_for_timeout(5400)
    expect(greeting).to_have_text(before)
    page.locator('#greeting-pause').click()
    page.emulate_media(reduced_motion='reduce')
    expect(page.locator('#greeting-pause')).to_be_disabled()
    page.wait_for_timeout(5400)
    expect(greeting).to_have_text(before)
    assert page.evaluate('document.getAnimations().length') == 0
    page.emulate_media(reduced_motion='no-preference')
    # Explicit document visibility fixture, not a claim about physical background tabs.
    page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true, get:() => true}); document.dispatchEvent(new Event('visibilitychange'));")
    page.wait_for_timeout(5400)
    expect(greeting).to_have_text(before)
    page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'));")
    expect(greeting).not_to_have_text(before, timeout=7000)
    passed('welcome: user pause, OS reduced motion and visibility-event pause/resume')
    context.close()


def connection_cases(browser, origin, capture):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    mode = {'value': 'unconfigured'}
    held = []

    def health_fixture(route):
        if mode['value'] == 'unconfigured':
            route.fulfill(json={'status': 'ok', 'llm_ready': False})
        elif mode['value'] == 'invalid':
            route.fulfill(json={'status': 'ok', 'llm_ready': 'yes'})
        elif mode['value'] == 'failure':
            route.abort()
        elif mode['value'] == 'hold':
            held.append(route)
        else:
            route.fulfill(json={'status': 'ok', 'llm_ready': True})

    context.route('**/api/v1/health', health_fixture)
    page.goto(origin + '/v2/index.html')
    status, retry = page.locator('#service-status'), page.locator('#health-retry')
    expect(status).to_have_text('API reachable')
    expect(page.locator('#service-detail')).to_have_text('Provider not configured · general replies unavailable.')
    expect(page.locator('#offline-banner')).to_be_hidden()
    passed('health: API reachability is separate from provider readiness')

    mode['value'] = 'invalid'
    retry.click()
    expect(page.locator('#offline-banner')).to_be_visible()
    expect(status).to_have_text('Service unavailable')
    mode['value'] = 'hold'
    retry.click()
    expect(status).to_have_text('Checking service…')
    expect(page.locator('#offline-banner')).to_be_visible()
    expect(retry).to_be_disabled()
    expect(page.locator('#offline-detail')).to_contain_text('timed out', timeout=10000)
    expect(retry).to_be_enabled()
    # Release the obsolete timed-out response; it must not paint a success state.
    held.pop().fulfill(json={'status': 'ok', 'llm_ready': True})
    expect(status).to_have_text('Service unavailable')
    passed('health: malformed response rejected, retry retains warning, timeout cannot be overwritten by stale success')
    mode['value'] = 'ok'
    retry.click()
    expect(status).to_have_text('API reachable')
    expect(page.locator('#offline-banner')).to_be_hidden()
    draft = page.locator('#message-input')
    draft.fill('An offline draft that matters.')
    context.set_offline(True)
    expect(status).to_have_text('Browser offline')
    shot(page, 'light-1440-offline', capture)
    page.locator('#theme-toggle').click()
    shot(page, 'dark-1440-offline', capture)
    expect(draft).to_have_value('An offline draft that matters.')
    context.set_offline(False)
    expect(status).to_have_text('API reachable')
    expect(page.locator('#offline-banner')).to_be_hidden()
    mode['value'] = 'failure'
    retry.click()
    expect(status).to_have_text('Service unavailable')
    mode['value'] = 'ok'
    retry.click()
    expect(status).to_have_text('API reachable')
    passed('health: browser offline/online and failed-fetch/retry recovery retain the draft')

    mode['value'] = 'hold'
    retry.click()
    expect(status).to_have_text('Checking service…')
    page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true, get:() => true}); document.dispatchEvent(new Event('visibilitychange'));")
    expect(status).to_have_text('Service check paused')
    held.pop().fulfill(json={'status': 'ok', 'llm_ready': True})
    expect(status).to_have_text('Service check paused')
    mode['value'] = 'ok'
    page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'));")
    expect(status).to_have_text('API reachable')
    passed('health: visibility event aborts pending request; foreground resumes without stale writes')
    context.close()


def storage_recovery(browser, origin):
    for mode in ('malformed', 'blocked'):
        context = browser.new_context(color_scheme='dark', reduced_motion='reduce', viewport={'width': 1440, 'height': 1000})
        context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))
        script = f"localStorage.setItem('{KEY}', '{{broken');" if mode == 'malformed' else (
            "Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('Blocked', 'SecurityError');}});")
        context.add_init_script(script)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/v2/index.html')
        expect(page.locator('html')).to_have_attribute('data-sidebar', 'expanded')
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        page.locator('#sidebar-toggle').click()
        expect(page.locator('html')).to_have_attribute('data-sidebar', 'collapsed')
        if mode == 'blocked':
            expect(page.locator('#toast-region')).to_contain_text('Browser storage is unavailable')
        assert not errors, errors
        passed(f'{mode} storage: shell boots with defaults and sidebar remains usable')
        context.close()


def live_smoke(browser, base):
    page = browser.new_page()
    response = page.request.get(base.rstrip('/') + '/api/v1/health')
    assert response.status == 200
    data = response.json()
    page.goto(base.rstrip('/') + '/static/v2/index.html')
    expect(page.locator('#service-status')).to_have_text('API reachable')
    expected = 'Provider configured' if data['llm_ready'] else 'Provider not configured'
    expect(page.locator('#service-detail')).to_contain_text(expected)
    page.close()
    passed('LIVE: actual FastAPI health 200 and shell status agree; no chat request')
    return {'health_http': response.status, 'status': data['status'], 'llm_ready': data['llm_ready']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--live')
    args = parser.parse_args()
    if args.capture:
        (ROOT / 'docs/screenshots/phase3').mkdir(exist_ok=True)
    server = PreviewServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'static')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            version = browser.version
            layout_and_interactions(browser, origin, args.capture)
            lifecycle(browser, origin)
            connection_cases(browser, origin, args.capture)
            storage_recovery(browser, origin)
            live = live_smoke(browser, args.live) if args.live else None
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {'phase': 3, 'environment': {'platform': platform.platform(), 'python': platform.python_version(), 'chromium': version},
              'scope': 'shell only; deterministic health fixtures plus optional separately labelled live smoke',
              'passed_groups': PASSED, 'live': live, 'screenshots': SHOTS}
    if args.capture:
        (ROOT / 'docs/shell-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'\n{len(PASSED)} shell check groups passed; {len(SHOTS)} screenshots; live smoke: {bool(live)}.')


if __name__ == '__main__':
    main()
