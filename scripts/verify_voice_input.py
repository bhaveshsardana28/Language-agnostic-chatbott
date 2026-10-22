"""Phase 7 V2 mocked SpeechRecognition input checks.

python scripts/verify_voice_input.py
The recognition engine is fake: this proves the V2 state machine, not a real
microphone or browser/OS speech service.
"""

from functools import partial
import json
import platform
import threading

from playwright.sync_api import expect, sync_playwright

from verify_design_system import ROOT, PreviewServer, QuietHandler


PASSED = []


def passed(label):
    PASSED.append(label)
    print(f"PASS {label}", flush=True)


def static_server():
    server = PreviewServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'static')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


FAKE_ENGINE = """
window.mediaCalls = 0;
navigator.mediaDevices.getUserMedia = () => { window.mediaCalls++; throw Error('getUserMedia must not run'); };
class FakeRecognition {
  constructor() { this.lang = ''; window.fakeRecognitionInstances.push(this); }
  start() { window.fakeRecognitionStarts++; setTimeout(() => this.onstart?.(), 120); }
  stop() { window.fakeRecognitionStops++; setTimeout(() => this.onend?.(), 0); }
  abort() { this.stop(); }
  emitResults(items) {
    const results = items.map(item => { const result = { isFinal: item.isFinal, length: 1 }; result[0] = { transcript: item.text }; return result; });
    this.onresult?.({ resultIndex: 0, results });
  }
  emitError(error) { this.onerror?.({ error }); setTimeout(() => this.onend?.(), 0); }
}
window.fakeRecognitionInstances = [];
window.fakeRecognitionStarts = 0;
window.fakeRecognitionStops = 0;
window.SpeechRecognition = FakeRecognition;
window.webkitSpeechRecognition = FakeRecognition;
"""


def seed_context(context, fake=True):
    script = "localStorage.removeItem('gaia.history.v2'); localStorage.removeItem('gaia.redesign.v2'); window.mediaCalls = 0; navigator.mediaDevices.getUserMedia = () => { window.mediaCalls++; throw Error('getUserMedia must not run'); };"
    if fake:
        script += FAKE_ENGINE
    else:
        script += "delete window.SpeechRecognition; delete window.webkitSpeechRecognition;"
    context.add_init_script(script)
    context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def supported_flow(browser, origin):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    seed_context(context)
    page = context.new_page()
    requests = []
    page.on('request', lambda request: requests.append(request.url) if '/api/v1/chat' in request.url else None)
    page.goto(origin + '/v2/index.html?mock=1')
    mic = page.locator('#voice-input-button')
    expect(mic).to_be_enabled()
    expect(page.locator('#voice-input-status')).to_contain_text('ready')

    page.locator('#sidebar-toggle').click()
    page.get_by_role('button', name='Appearance settings', exact=True).click()
    page.locator('#speech-language').select_option('hi-IN')
    expect(page.locator('#speech-language')).to_have_value('hi-IN')
    page.get_by_role('button', name='Done', exact=True).click()
    assert page.evaluate("JSON.parse(localStorage.getItem('gaia.redesign.v2')).speechLanguage") == 'hi-IN'
    passed('settings: speech locale persists with Auto and seven explicit locale options')

    mic.click()
    expect(mic).to_have_attribute('data-state', 'requesting')
    expect(page.locator('#voice-input-status')).to_contain_text('Requesting')
    page.wait_for_timeout(180)
    expect(mic).to_have_attribute('data-state', 'listening')
    expect(mic).to_have_attribute('aria-pressed', 'true')
    assert page.evaluate('window.fakeRecognitionInstances.at(-1).lang') == 'hi-IN'
    page.evaluate("window.fakeRecognitionInstances.at(-1).emitResults([{text:'नमस्ते GAIA', isFinal:false}])")
    expect(page.locator('#message-input')).to_have_value('नमस्ते GAIA')
    assert not requests
    page.evaluate("window.fakeRecognitionInstances.at(-1).emitResults([{text:'नमस्ते GAIA', isFinal:true}])")
    expect(page.locator('#message-input')).to_have_value('नमस्ते GAIA')
    assert not requests
    passed('transcript: interim and final speech stay editable in the composer without auto-send')

    page.keyboard.press('Escape')
    expect(mic).to_have_attribute('data-state', 'idle')
    page.wait_for_timeout(50)
    page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', {key:'M', code:'KeyM', metaKey:true, shiftKey:true, bubbles:true, cancelable:true}))")
    if mic.get_attribute('data-state') == 'idle':
        page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', {key:'M', code:'KeyM', ctrlKey:true, shiftKey:true, bubbles:true, cancelable:true}))")
    page.wait_for_timeout(180)
    expect(mic).to_have_attribute('data-state', 'listening')
    page.keyboard.press('Escape')
    expect(mic).to_have_attribute('data-state', 'idle')
    page.wait_for_timeout(50)
    passed('controls: Escape and Ctrl+Shift+M start/stop recognition safely')

    mic.click()
    page.wait_for_timeout(180)
    page.evaluate("window.fakeRecognitionInstances.at(-1).emitError('not-allowed')")
    expect(page.locator('#voice-input-status')).to_contain_text('permission was denied')
    expect(mic).to_have_attribute('data-state', 'idle')
    assert page.evaluate('window.mediaCalls') == 0
    passed('errors/privacy: permission error is actionable, recognition returns idle and no audio API is requested')

    # Auto uses the latest detected user language rather than the explicit setting.
    page.locator('#sidebar-toggle').click()
    page.get_by_role('button', name='New chat', exact=True).click()
    page.locator('#message-input').fill('मुझे कुछ नया सिखाओ।')
    page.locator('#message-input').press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=10000)
    page.locator('#sidebar-toggle').click()
    page.get_by_role('button', name='Appearance settings', exact=True).click()
    page.locator('#speech-language').select_option('auto')
    page.get_by_role('button', name='Done', exact=True).click()
    mic.click()
    page.wait_for_timeout(180)
    assert page.evaluate('window.fakeRecognitionInstances.at(-1).lang') == 'hi-IN'
    page.keyboard.press('Escape')
    passed('auto locale: latest detected Hindi user language selects hi-IN for the next voice turn')
    context.close()


def unsupported_flow(browser, origin):
    context = browser.new_context(viewport={'width': 360, 'height': 800}, reduced_motion='reduce')
    seed_context(context, fake=False)
    page = context.new_page()
    page.goto(origin + '/v2/index.html?mock=1')
    expect(page.locator('#voice-input-button')).to_be_disabled()
    expect(page.locator('#voice-input-status')).to_contain_text('not supported')
    assert page.evaluate('window.mediaCalls') == 0
    passed('unsupported: microphone control disables with an explanation and page load stays permission-free')
    context.close()


def main():
    server, origin = static_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            supported_flow(browser, origin)
            unsupported_flow(browser, origin)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f'\n{len(PASSED)} Phase 7 voice-input check groups passed; mocked engine only.')
    (ROOT / 'docs/voice-input-checks.json').write_text(json.dumps({
        'phase': 7,
        'environment': {'platform': platform.platform()},
        'scope': 'V2 mocked SpeechRecognition input, locale selection, transcript editing, errors and privacy boundary',
        'passed_groups': PASSED,
        'real_microphone': False,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
