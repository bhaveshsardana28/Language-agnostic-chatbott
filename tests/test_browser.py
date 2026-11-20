"""Browser smoke test for the default GAIA V2 frontend.

Run with the FastAPI app already running:
    venv/bin/python tests/test_browser.py
"""

import os
import sys



BASE = os.environ.get('GAIA_BASE', 'http://127.0.0.1:8000')


def run(playwright):
    from playwright.sync_api import expect
    name = os.environ.get("GAIA_BROWSER", "chromium")
    browser = (playwright.chromium.launch(channel="chrome") if name == "chrome"
               else getattr(playwright, name).launch())
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)

    page.goto(BASE, wait_until='networkidle')
    expect(page).to_have_url(f'{BASE}/static/v2/index.html')
    expect(page.locator('#welcome')).to_be_visible()
    expect(page.locator('#message-input')).to_be_visible()
    assert page.locator('.app').count() == 0, 'legacy frontend shell is visible at the default route'
    print('PASS default localhost route opens the V2 frontend')

    for width in (320, 375, 425, 768, 1024, 1280, 1440):
        page.set_viewport_size({"width": width, "height": 850})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        expect(page.locator("#message-input")).to_be_in_viewport()
    print(f"PASS {name} welcome and composer fit all seven viewport widths")

    page.set_viewport_size({"width": 320, "height": 740})
    draft = page.locator('#message-input')
    reply_options = page.get_by_role('button', name='Language options')
    reply_options.click()
    page.locator('#reply-language').select_option('Hindi')
    page.get_by_role('button', name='Apply to draft').click()
    expect(draft).to_be_focused()
    expect(page.locator('#send-button')).to_be_disabled()
    draft.press_sequentially('How are you?')
    expect(draft).to_have_value('How are you?\nReply in Hindi.')
    reply_options.click()
    expect(page.locator('#reply-language')).to_have_value('Hindi')
    page.locator('#reply-language').select_option('')
    page.get_by_role('button', name='Apply to draft').click()
    expect(draft).to_be_focused()
    expect(draft).to_have_value('How are you?')
    expect(page.locator('#send-button')).to_be_enabled()
    print('PASS mobile reply-language selection, automatic reset and intact draft')

    page.locator('#message-input').fill('What is 19 plus 23? Answer in digits.')
    page.locator('#message-input').press('Enter')
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_be_visible(timeout=30000)
    expect(page.locator('.chat-message--assistant')).to_contain_text('42', timeout=1000)
    page.reload()
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_contain_text('42')
    with page.expect_response(lambda response: response.url.endswith('/api/v1/chat') and response.request.method == 'POST') as sent:
        page.get_by_role('button', name='Retry', exact=True).click()
    assert sent.value.status == 200 and sent.value.request.post_data_json['replace_reply'] > 0
    expect(page.locator('.chat-message--assistant[aria-busy="false"]')).to_contain_text('42')
    expect(page.locator('.chat-message--user')).to_have_count(1)
    expect(page.locator('.chat-message--assistant')).to_have_count(1)
    assert not errors, errors
    print('PASS default V2 route sends and renders a general model reply')
    browser.close()


if __name__ == '__main__':
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as playwright:
            run(playwright)
    except Exception as error:
        print(f'FAIL {error}', file=sys.stderr)
        raise
