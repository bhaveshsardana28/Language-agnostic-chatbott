"""Phase 5 multilingual metadata and explainability checks.

python scripts/verify_languages.py [--capture]
The browser uses the actual V2 page in mock mode, so this check is deterministic
and never requires an LLM key or a network chat request.
"""

import argparse
from functools import partial
import json
import platform
import threading

from playwright.sync_api import expect, sync_playwright

from verify_design_system import ROOT, PreviewServer, QuietHandler


PASSED = []
SHOTS = []


def passed(label):
    PASSED.append(label)
    print(f"PASS {label}", flush=True)


def static_server():
    server = PreviewServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'static')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def seed_context(context):
    context.add_init_script("""
      localStorage.removeItem('gaia.redesign.v2');
      window.languageCheckErrors = [];
    """)
    context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def screenshot(page, name, capture):
    if capture:
        path = ROOT / 'docs/screenshots/phase5' / f'{name}.png'
        page.screenshot(path=str(path), full_page=True, animations='disabled')
        SHOTS.append(str(path.relative_to(ROOT)))


def run_checks(browser, origin, capture):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    seed_context(context)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    page.goto(origin + '/v2/index.html?mock=1')
    expect(page.locator('#service-status')).to_have_text('API reachable')

    input_box = page.locator('#message-input')
    input_box.fill('Explain a small idea')
    input_box.press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=10000)
    expect(page.locator('.chat-message--user .language-chip')).to_contain_text('English')
    expect(page.locator('.chat-message--assistant .language-chip')).to_contain_text('English')
    expect(page.locator('.chat-message--assistant .script-chip')).to_have_text('Latin script')
    expect(page.locator('#shell-language-label')).to_have_text('English')
    expect(page.locator('#shell-language-detail')).to_have_text('· Latin')
    assert page.locator('.chat-message--user').get_attribute('dir') == 'auto'
    assert page.locator('.chat-message--assistant').get_attribute('dir') == 'auto'
    assert page.locator('.chat-message--assistant .chat-insights').count() == 1
    expect(page.locator('.chat-message--assistant .chat-insights')).to_be_hidden()
    passed('metadata: native/English language labels, script label, confidence boundary and auto direction')

    page.get_by_role('button', name='Appearance settings', exact=True).click()
    settings = page.locator('#settings-dialog')
    expect(settings).to_be_visible()
    expect(page.locator('#show-insights')).not_to_be_checked()
    page.locator('#show-insights').check()
    settings.get_by_role('button', name='Done', exact=True).click()
    expect(page.locator('html')).to_have_attribute('data-debug', 'true')
    assert page.evaluate("JSON.parse(localStorage.getItem('gaia.redesign.v2')).debug") is True
    expect(page.locator('.chat-message--assistant .chat-insights')).to_be_visible()
    expect(page.locator('.chat-message--assistant .chat-insights')).to_contain_text('Detection confidence')
    expect(page.locator('.chat-message--assistant .chat-insights')).to_contain_text('Response language')
    passed('insights: default-off toggle persists and reveals real reply metadata')

    input_box.fill('मुझे कुछ नया सिखाओ।')
    input_box.press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_have_count(2, timeout=10000)
    expect(page.locator('.chat-message--user').nth(1).locator('.language-chip')).to_contain_text('हिन्दी')
    expect(page.locator('.chat-message--assistant').nth(1).locator('.language-chip')).to_contain_text('Hindi')
    expect(page.locator('#shell-language-label')).to_contain_text('Hindi')
    expect(page.locator('#shell-language-detail')).to_have_text('· Devanagari')
    expect(page.locator('.language-switch')).to_have_count(1)
    expect(page.locator('.language-switch')).to_contain_text('Language switched')
    expect(page.locator('.language-switch')).to_contain_text('Hindi')
    passed('switching: divider appears once only when assistant response language changes')

    input_box.fill('uncertain mixed language')
    input_box.press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_have_count(3, timeout=10000)
    low_chip = page.locator('.chat-message--user').nth(2).locator('.language-chip')
    expect(low_chip).to_have_class('chip language-chip language-chip--low')
    expect(low_chip).to_have_attribute('title', 'Detection confidence 35% — verify language')
    screenshot(page, 'dark-1440-multilingual', capture)
    assert not errors, errors
    passed('low-confidence: dashed language hint and accessible verification title are exposed')
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if args.capture:
        (ROOT / 'docs/screenshots/phase5').mkdir(exist_ok=True)
    server, origin = static_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            run_checks(browser, origin, args.capture)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f'\n{len(PASSED)} Phase 5 check groups passed; {len(SHOTS)} screenshots.')
    report = {
        'phase': 5,
        'environment': {'platform': platform.platform(), 'python': platform.python_version()},
        'scope': 'per-message language metadata, switching dividers, direction, confidence hints and Insights',
        'passed_groups': PASSED,
        'screenshots': SHOTS,
    }
    if args.capture:
        (ROOT / 'docs/language-checks.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
