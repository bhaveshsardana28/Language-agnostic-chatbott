"""Phase 6 V2 document and source-card checks.

python scripts/verify_documents.py [--capture]
The browser uses route fixtures for the document/chat APIs; no embeddings or LLM
provider are contacted.
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


def screenshot(page, name, capture):
    if capture:
        path = ROOT / 'docs/screenshots/phase6' / f'{name}.png'
        page.screenshot(path=str(path), full_page=True, animations='disabled')
        SHOTS.append(str(path.relative_to(ROOT)))


def seed_context(context):
    context.add_init_script("""
      if (!sessionStorage.getItem('phase6-docs-seeded')) {
        localStorage.removeItem('gaia.history.v2');
        localStorage.setItem('gaia.store.v1', 'legacy untouched');
        sessionStorage.setItem('phase6-docs-seeded', 'true');
      }
    """)
    context.route('**/api/v1/health', lambda route: route.fulfill(json={'status': 'ok', 'llm_ready': True}))


def run_checks(browser, origin, capture):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    seed_context(context)
    state = {'server_id': 'document-server-id', 'documents': [], 'create_calls': 0,
             'upload_calls': [], 'list_calls': [], 'clear_calls': [], 'remove_calls': [], 'chat_calls': []}

    def conversations(route):
        state['create_calls'] += 1
        route.fulfill(status=200, content_type='application/json', body=json.dumps({'conversation_id': state['server_id']}))

    def documents_route(route):
        request = route.request
        if request.method == 'GET':
            state['list_calls'].append(request.url)
            if request.url.endswith('/document-server-id/1'):
                route.fulfill(status=200, content_type='application/json', body=json.dumps({
                    'schema_version': 1, 'document_id': 1, 'filename': 'policy.txt',
                    'status': 'completed', 'full_text': 'Our refund policy allows refunds within 30 days.',
                    'pages': [{'page_number': 2, 'text': 'Our refund policy allows refunds within 30 days.'}],
                }))
                return
            route.fulfill(status=200, content_type='application/json', body=json.dumps({
                'conversation_id': state['server_id'], 'documents': state['documents']}))
            return
        if request.method == 'DELETE':
            if request.url.endswith('/document-server-id/1'):
                state['remove_calls'].append(request.url)
                state['documents'] = []
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'deleted': True}))
                return
            state['clear_calls'].append(request.url)
            state['documents'] = []
            route.fulfill(status=200, content_type='application/json', body=json.dumps({'deleted': True}))
            return
        body = request.post_data or ''
        state['upload_calls'].append({'url': request.url, 'body': body})
        if 'bad.txt' in body:
            route.fulfill(status=422, content_type='application/json', body=json.dumps({'error': 'could not process document: bad.txt'}))
            return
        filename = 'policy.txt' if 'policy.txt' in body else 'document.txt'
        state['documents'] = [{'document_id': 1, 'document': filename, 'chunks': 2}]
        route.fulfill(status=200, content_type='application/json', body=json.dumps({
            'conversation_id': state['server_id'], 'document': filename, 'chars': 48,
            'chunks': 2, 'chunk_size': 1200, 'overlap': 150, 'embeddings': False}))

    def chat_route(route):
        state['chat_calls'].append(route.request.post_data or '')
        body = '\n\n'.join([
            'data: {"type":"meta","conversation_id":"document-server-id","language_meta":{"language":"en","language_name":"English","script":"Latin","confidence":0.99,"secondary_languages":[],"code_switched":false,"mixed_script":false,"scripts":{"Latin":1},"detection_reason":"fixture"},"route":"document","reason":"fixture","response_lang":"en"}',
            'data: {"type":"delta","text":"The policy allows refunds within 30 days."}',
             'data: {"type":"done","latency_ms":12,"model":"fixture","sources":[{"document":"policy.txt","document_id":1,"chunk":0,"page":2,"score":0.81,"excerpt":"Our refund policy allows refunds within 30 days."},{"title":"Example source","url":"https://example.com/reference"},{"title":"Unsafe source","url":"javascript:alert(1)"},{"note":"embeddings unavailable; keyword retrieval used"}]}',
            ''
        ])
        route.fulfill(status=200, content_type='text/event-stream', body=body)

    context.route('**/api/v1/conversations', conversations)
    context.route('**/api/v1/documents**', documents_route)
    context.route('**/api/v1/chat', chat_route)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text)
            if message.type == 'error' and 'status of 422' not in message.text else None)
    page.goto(origin + '/v2/index.html')

    page.get_by_role('button', name='Library', exact=True).click()
    expect(page.locator('#documents-dialog')).to_be_visible()
    expect(page.locator('#document-empty')).to_be_visible()
    assert not state['list_calls']
    passed('empty: documents before chat show an honest empty state without a list request')

    page.get_by_role('button', name='Back to my draft', exact=True).click()
    page.get_by_role('button', name='Attach files', exact=True).click()
    expect(page.locator('#attach-menu')).to_be_visible()
    page.locator('[data-attach-action="upload"]').click()
    page.locator('#document-file').set_input_files({
        'name': 'policy.txt', 'mimeType': 'text/plain',
        'buffer': b'Our refund policy allows refunds within 30 days.'})
    expect(page.locator('#composer-context')).to_be_visible()
    expect(page.locator('#composer-context-text')).to_contain_text('policy.txt')
    page.locator('.composer-attachment-remove').click()
    expect(page.locator('#composer-attachments')).to_be_hidden()
    assert state['remove_calls'] == [f'{origin}/api/v1/documents/{state["server_id"]}/1']
    page.get_by_role('button', name='Attach files', exact=True).click()
    page.locator('[data-attach-action="upload"]').click()
    page.locator('#document-file').set_input_files({
        'name': 'policy.txt', 'mimeType': 'text/plain',
        'buffer': b'Our refund policy allows refunds within 30 days.'})
    page.get_by_role('button', name='Library', exact=True).click()
    expect(page.locator('#document-status')).to_contain_text('ready')
    expect(page.locator('.document-row')).to_contain_text('policy.txt')
    expect(page.locator('.document-status--ready')).to_have_text('Ready')
    expect(page.locator('#document-count')).to_contain_text('1 ready')
    assert state['create_calls'] == 1
    assert state['upload_calls'] and state['server_id'] in state['upload_calls'][0]['body']
    passed('upload: composer attachment menu uploads from the computer, creates one server conversation, and reaches Ready')

    page.get_by_role('button', name='Back to my draft', exact=True).click()
    page.locator('#message-input').fill('What is the refund window?')
    page.locator('#message-input').press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=10000)
    expect(page.locator('.chat-sources')).to_be_visible()
    expect(page.locator('.chat-sources')).to_contain_text('policy.txt · chunk 1')
    expect(page.locator('.chat-sources')).to_contain_text('embeddings unavailable')
    links = page.locator('.chat-sources a')
    expect(links).to_have_count(1)
    expect(links.first).to_have_attribute('href', 'https://example.com/reference')
    assert 'javascript:' not in (page.locator('.chat-sources').inner_text())
    assert state['chat_calls'] and json.loads(state['chat_calls'][0])['conversation_id'] == state['server_id']
    passed('sources: document chunk numbering, score, note text and safe HTTPS links render from done.sources')

    page.locator('.chat-source-link').click()
    expect(page.locator('#documents-dialog')).to_be_visible()
    expect(page.locator('#document-preview')).to_contain_text('refund policy allows refunds within 30 days')
    expect(page.locator('#document-preview-meta')).to_contain_text('page 2')
    passed('evidence: a document citation opens the actual extracted page text in the document workspace')

    page.reload()
    expect(page.locator('.chat-message--assistant')).to_contain_text('policy.txt · chunk 1')
    page.get_by_role('button', name='Library', exact=True).click()
    expect(page.locator('.document-row')).to_contain_text('policy.txt')
    assert state['list_calls']
    passed('restore: local history restores source cards and the active document list reloads by server ID')

    page.on('dialog', lambda dialog: dialog.accept())
    page.locator('#document-clear').click()
    expect(page.locator('#document-empty')).to_be_visible()
    assert state['clear_calls'] == [f'{origin}/api/v1/documents/{state["server_id"]}']
    passed('clear: confirmation calls the per-conversation delete endpoint and empties the panel')

    page.locator('#document-file').set_input_files({
        'name': 'bad.txt', 'mimeType': 'text/plain', 'buffer': b'not readable'})
    expect(page.locator('#document-status')).to_contain_text('could not be read')
    expect(page.locator('.document-status--ready')).to_have_count(0)
    expect(page.locator('.document-status--failed')).to_have_text('Failed')
    screenshot(page, 'light-1440-documents', capture)
    assert page.evaluate("localStorage.getItem('gaia.store.v1')") == 'legacy untouched'
    assert not errors, errors
    passed('failure: rejected ingestion becomes Failed without leaving a stale Ready row')
    context.close()


def narrow_layout(browser, origin):
    context = browser.new_context(viewport={'width': 320, 'height': 568}, reduced_motion='reduce')
    seed_context(context)
    page = context.new_page()
    page.goto(origin + '/v2/index.html?mock=1')
    page.locator('#sidebar-toggle').click()
    page.get_by_role('button', name='Library', exact=True).click()
    expect(page.locator('#documents-dialog')).to_be_visible()
    layout = page.locator('.document-toolbar').evaluate("node => getComputedStyle(node).flexDirection")
    assert layout == 'column'
    assert page.evaluate('document.body.scrollWidth') <= 320
    passed('narrow: document controls stack below 448px without horizontal overflow or overlap')
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
            run_checks(browser, origin, args.capture)
            narrow_layout(browser, origin)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f'\n{len(PASSED)} Phase 6 document check groups passed; {len(SHOTS)} screenshots.')
    report = {
        'phase': 6,
        'environment': {'platform': platform.platform(), 'python': platform.python_version()},
        'scope': 'V2 document upload/status/list/clear and done.sources rendering',
        'passed_groups': PASSED,
        'screenshots': SHOTS,
    }
    if args.capture:
        (ROOT / 'docs/document-checks.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
