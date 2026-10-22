"""Phase 6 V2 local conversation history checks.

python scripts/verify_history.py [--capture]
The browser uses the deterministic V2 mock stream; no provider key is needed.
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


def seed_context(context, mode='clean'):
    setup = "localStorage.removeItem('gaia.history.v2'); localStorage.setItem('gaia.store.v1', 'legacy untouched');"
    if mode == 'malformed':
        setup = "localStorage.setItem('gaia.history.v2', '{broken'); localStorage.setItem('gaia.store.v1', 'legacy untouched');"
    if mode == 'blocked':
        setup = """
          localStorage.removeItem('gaia.history.v2');
          localStorage.setItem('gaia.store.v1', 'legacy untouched');
          const originalSetItem = Storage.prototype.setItem;
          Storage.prototype.setItem = function(key, value) {
            if (key === 'gaia.history.v2') throw new DOMException('quota', 'QuotaExceededError');
            return originalSetItem.call(this, key, value);
          };
        """
    context.add_init_script(f"""
      if (!sessionStorage.getItem('phase6-seeded')) {{
        {setup}
        sessionStorage.setItem('phase6-seeded', 'true');
      }}
    """)
    context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def screenshot(page, name, capture):
    if capture:
        path = ROOT / 'docs/screenshots/phase6' / f'{name}.png'
        page.screenshot(path=str(path), full_page=True, animations='disabled')
        SHOTS.append(str(path.relative_to(ROOT)))


def wait_for_reply(page, count=1):
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_have_count(count, timeout=10000)


def open_history_menu(page, record_id):
    page.locator(f'[data-history-menu="{record_id}"]').click()


def history_flow(browser, origin, capture):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    seed_context(context)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(origin + '/v2/index.html?mock=1')

    input_box = page.locator('#message-input')
    input_box.fill('Explain a small idea')
    input_box.press('Enter')
    wait_for_reply(page)
    expect(page.locator('[data-history-id]')).to_have_count(1)
    expect(page.locator('.history-group-title')).to_have_text('Today')
    saved = page.evaluate("JSON.parse(localStorage.getItem('gaia.history.v2'))")
    record = saved['conversations'][0]
    assert record['serverId'] == 'mock-phase4-conversation'
    assert len(record['messages']) == 2
    assert all('article' not in json.dumps(message) for message in record['messages'])
    passed('persist: V2 history stores title, server ID, turns and no DOM runtime objects')

    page.reload()
    expect(page.locator('#conversation-view')).to_be_visible()
    expect(page.locator('.chat-message')).to_have_count(2)
    expect(page.locator('.chat-message--assistant')).to_contain_text('Start with')
    expect(page.locator('.chat-message--assistant .language-chip')).to_contain_text('English')
    passed('restore: reload reconstructs the conversation, metadata and assistant rendering')

    page.get_by_role('button', name='New chat', exact=True).click()
    expect(page.locator('#welcome')).to_be_visible()
    expect(page.locator('#message-log')).to_be_empty()
    expect(page.locator('[data-history-id]')).to_have_count(1)
    input_box.fill('मुझे कुछ नया सिखाओ।')
    input_box.press('Enter')
    wait_for_reply(page)
    expect(page.locator('[data-history-id]')).to_have_count(2)
    expect(page.locator('[data-history-id]').first).to_contain_text('मुझे')
    page.locator('[data-history-id]').nth(1).click()
    expect(page.locator('.chat-message')).to_have_count(2)
    expect(page.locator('.chat-message--user')).to_contain_text('Explain a small idea')
    passed('switch: New chat preserves old history and selecting a row restores without duplicates')

    page.locator('#history-search').fill('small idea')
    expect(page.locator('[data-history-id]')).to_have_count(1)
    expect(page.locator('.history-snippet')).to_contain_text('small idea')
    page.locator('#history-search').fill('no such conversation')
    expect(page.locator('#history-no-results')).to_be_visible()
    expect(page.locator('[data-history-id]')).to_have_count(0)
    page.locator('#history-search').fill('')
    passed('search: title/message filtering, content snippet and explicit no-results state')

    page.keyboard.press('Control+K')
    expect(page.locator('#search-dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#search-dialog')).to_be_hidden()
    page.get_by_role('button', name='Search chats', exact=True).click()
    expect(page.locator('#search-dialog')).to_be_visible()
    expect(page.locator('#search-dialog-input')).to_be_focused()
    page.locator('#search-dialog-input').fill('small idea')
    expect(page.locator('[data-search-history-id]')).to_have_count(1)
    page.locator('[data-search-history-id]').click()
    expect(page.locator('#search-dialog')).to_be_hidden()
    expect(page.locator('#conversation-heading')).to_contain_text('Explain a small idea')
    passed('search dialog: local title/message search focuses on open, returns a result and restores its conversation')

    current_id = page.locator('[data-history-id][aria-current="true"]').get_attribute('data-history-id')
    open_history_menu(page, current_id)
    page.locator(f'[data-record-id="{current_id}"][data-history-action="rename"]').click()
    expect(page.locator('#rename-dialog')).to_be_visible()
    page.locator('#rename-input').fill('   ')
    page.locator('#rename-form').press('Enter')
    expect(page.locator('#rename-error')).to_contain_text('Add a title')
    page.locator('#rename-input').fill('A renamed thought')
    page.locator('#rename-form').press('Enter')
    expect(page.locator('#conversation-heading')).to_have_text('A renamed thought')
    assert page.evaluate("JSON.parse(localStorage.getItem('gaia.history.v2')).conversations.some(c => c.title === 'A renamed thought')")
    passed('rename: accessible dialog validates, trims and synchronizes sidebar/header/storage')

    current_id = page.locator('[data-history-id][aria-current="true"]').get_attribute('data-history-id')
    open_history_menu(page, current_id)
    with page.expect_download() as download_info:
        page.locator(f'[data-record-id="{current_id}"][data-history-action="export"]').click()
    download = download_info.value
    assert download.suggested_filename == 'A-renamed-thought.md'
    export_text = open(download.path(), encoding='utf-8').read()
    assert '# A renamed thought' in export_text and '## You ·' in export_text and '_Language: en_' in export_text
    passed('export: selected conversation downloads a sanitized Markdown transcript with roles and language')

    open_history_menu(page, current_id)
    page.locator(f'[data-record-id="{current_id}"][data-history-action="delete"]').click()
    expect(page.locator('#delete-dialog')).to_be_visible()
    page.get_by_role('button', name='Keep conversation', exact=True).click()
    expect(page.locator('[data-history-id]')).to_have_count(2)
    open_history_menu(page, current_id)
    page.locator(f'[data-record-id="{current_id}"][data-history-action="delete"]').click()
    page.locator('#delete-form button[type="submit"]').click()
    expect(page.locator('[data-history-id]')).to_have_count(1)
    passed('delete: cancel is a no-op and confirmation removes the selected local record')
    screenshot(page, 'light-1440-history', capture)
    assert not errors, errors
    context.close()


def mobile_drawer_history_flow(browser, origin):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
    seed_context(context)
    context.add_init_script("""
      const now = Date.now();
      localStorage.setItem('gaia.history.v2', JSON.stringify({
        version: 1, currentId: 'mobile-current', conversations: [
          { id: 'mobile-current', serverId: null, title: 'Current thought', createdAt: now - 1000,
            updatedAt: now - 1000, messages: [
              { id: 'mobile-current-user', role: 'user', text: 'Current message', timestamp: now - 1000, meta: {} },
              { id: 'mobile-current-assistant', role: 'assistant', text: 'Current reply', timestamp: now - 900, meta: { response_lang: 'en' } }
            ] },
          { id: 'mobile-saved', serverId: null, title: 'Saved thought', createdAt: now - 2000,
            updatedAt: now - 2000, messages: [
              { id: 'mobile-saved-user', role: 'user', text: 'Saved message', timestamp: now - 2000, meta: {} },
              { id: 'mobile-saved-assistant', role: 'assistant', text: 'Saved reply', timestamp: now - 1900, meta: { response_lang: 'en' } }
            ] }
        ]
      }));
    """)
    page = context.new_page()
    page.goto(origin + '/v2/index.html?mock=1')
    drawer = page.locator('#navigation-drawer')
    toggle = page.locator('#sidebar-toggle')
    expect(page.locator('[data-history-id]')).to_have_count(2)

    toggle.click()
    page.locator('[data-history-id="mobile-saved"]').click()
    expect(drawer).to_be_hidden()
    expect(toggle).to_be_focused()
    expect(page.locator('[data-history-id="mobile-saved"]')).to_have_attribute('aria-current', 'true')
    passed('mobile row selection: drawer closes and navigation toggle regains focus')

    toggle.click()
    open_history_menu(page, 'mobile-saved')
    page.locator('[data-record-id="mobile-saved"][data-history-action="rename"]').click()
    expect(drawer).to_be_hidden()
    expect(page.locator('#rename-dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#rename-dialog')).to_be_hidden()
    expect(toggle).to_be_focused()
    passed('mobile rename: dialog opens after closing drawer and Escape restores toggle focus')

    toggle.click()
    open_history_menu(page, 'mobile-saved')
    with page.expect_download() as download_info:
        page.locator('[data-record-id="mobile-saved"][data-history-action="export"]').click()
    download = download_info.value
    expect(drawer).to_be_hidden()
    assert download.suggested_filename == 'Saved-thought.md'
    passed('mobile export: transcript downloads after closing drawer')

    toggle.click()
    open_history_menu(page, 'mobile-saved')
    page.locator('[data-record-id="mobile-saved"][data-history-action="delete"]').click()
    expect(drawer).to_be_hidden()
    expect(page.locator('#delete-dialog')).to_be_visible()
    page.locator('#delete-form button[type="submit"]').click()
    expect(page.locator('#delete-dialog')).to_be_hidden()
    expect(drawer).to_be_hidden()
    expect(page.locator('[data-history-id]')).to_have_count(1)
    passed('mobile delete: confirmation leaves drawer closed and removes the record')
    context.close()


def malformed_storage(browser, origin):
    context = browser.new_context(viewport={'width': 768, 'height': 900}, reduced_motion='reduce')
    seed_context(context, 'malformed')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(origin + '/v2/index.html?mock=1')
    expect(page.locator('#welcome')).to_be_visible()
    assert page.locator('#history-empty').get_attribute('hidden') is None
    assert not errors, errors
    passed('malformed: invalid V2 history falls back to an empty usable shell')
    context.close()


def server_delete(browser, origin):
    context = browser.new_context(viewport={'width': 768, 'height': 900}, reduced_motion='reduce')
    seed_context(context)
    cid = 'server-history-cid'
    context.add_init_script(f"""
      localStorage.setItem('gaia.history.v2', JSON.stringify({{
        version: 1, currentId: 'local-history-id', conversations: [{{
          id: 'local-history-id', serverId: '{cid}', title: 'Server cleanup',
          createdAt: Date.now(), updatedAt: Date.now(), messages: [{{
            id: 'stored-user', role: 'user', text: 'Saved server turn', timestamp: Date.now(), meta: {{}}
          }}]
        }}]
      }}));
    """)
    requests = []
    context.route(f'**/api/v1/chat/{cid}', lambda route: (requests.append(route.request.url), route.fulfill(json={'deleted': True, 'documents_deleted': 1})))
    page = context.new_page()
    page.goto(origin + '/v2/index.html')
    page.get_by_role('button', name='Open navigation').click()
    expect(page.locator('[data-history-id]')).to_have_count(1)
    open_history_menu(page, 'local-history-id')
    page.locator(f'[data-record-id="local-history-id"][data-history-action="delete"]').click()
    page.locator('#delete-form button[type="submit"]').click()
    expect(page.locator('#welcome')).to_be_visible()
    assert requests == [f'{origin}/api/v1/chat/{cid}']
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
    passed('server cleanup: confirmed delete uses the server ID and preserves legacy storage')
    context.close()


def blocked_storage(browser, origin):
    context = browser.new_context(viewport={'width': 768, 'height': 900}, reduced_motion='reduce')
    seed_context(context, 'blocked')
    page = context.new_page()
    page.goto(origin + '/v2/index.html?mock=1')
    page.locator('#message-input').fill('Storage can fail safely')
    page.locator('#message-input').press('Enter')
    wait_for_reply(page)
    expect(page.locator('#toast-region')).to_contain_text('storage is unavailable')
    expect(page.locator('.chat-message--assistant')).to_be_visible()
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
    passed('blocked: storage failure leaves the current-tab chat usable and protects legacy storage')
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if args.capture:
        (ROOT / 'docs/screenshots/phase6').mkdir(exist_ok=True)
    server, origin = static_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            history_flow(browser, origin, args.capture)
            mobile_drawer_history_flow(browser, origin)
            malformed_storage(browser, origin)
            server_delete(browser, origin)
            blocked_storage(browser, origin)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f'\n{len(PASSED)} Phase 6 check groups passed; {len(SHOTS)} screenshots.')
    report = {
        'phase': 6,
        'environment': {'platform': platform.platform(), 'python': platform.python_version()},
        'scope': 'V2 local history persistence, restoration, switching, malformed storage and storage failure',
        'passed_groups': PASSED,
        'screenshots': SHOTS,
    }
    if args.capture:
        (ROOT / 'docs/history-checks.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
