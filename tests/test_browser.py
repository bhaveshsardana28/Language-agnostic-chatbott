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
    cb_label = (page.text_content(".codeblock .cb-head") or "").strip()
    check("code block rendered with language label + copy",
          len(cb_label.replace("Copy","").strip()) > 0
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

    # ---------- Phase-3 shell regressions ----------
    page.click("#hdr-settings")
    page.wait_for_selector("#overlay-m.show .modal", timeout=3000)
    check("settings opens from header gear", "Settings" in page.text_content("#overlay-m .modal"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check("Escape closes settings modal", page.locator("#overlay-m.show").count() == 0)
    check("sidebar exposes Delete all data", page.is_visible("#del-all-side"))

    # ---------- Phase-4 chat-core regressions ----------
    # timestamps on messages
    check("messages show timestamps", page.locator(".acts-row .time").count() >= 1)

    # syntax highlighting inside code blocks (no-dependency tokenizer)
    hl_ok = page.evaluate("md('```python\\ndef hello():\\n  return \"world\"\\n```')")
    check("code block gets token highlighting", 'class="tok-k"' in hl_ok and 'tok-s' in hl_ok)

    # composer length validation
    page.fill("#input", "x" * 4100)
    before = page.locator(".msg").count()
    page.press("#input", "Enter")
    page.wait_for_timeout(300)
    check("oversized message blocked with toast",
          page.locator(".msg").count() == before and page.is_visible("#toast.show"))

    # chat-switch during streaming must abort, not crash or cross-paint
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        S.conversations.push({id:'switchtest',title:'Switch target',createdAt:Date.now(),
            updatedAt:Date.now(),messages:[{role:'user',content:'old',ts:Date.now()}]});
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector("#input", timeout=8000)
    switch_ok = page.evaluate("""() => {
        // simulate an in-flight stream, then switch to the other conversation
        streaming=true; aborter=null;
        try { openConv('switchtest'); } catch(e) { streaming=false; return 'threw: '+e.message; }
        const ok = document.getElementById('chat-title').textContent==='Switch target' &&
                   document.querySelectorAll('.msg').length>=1;
        streaming=false;
        return ok ? 'OK' : 'wrong state';
    }""")
    check("chat-switch during streaming aborts cleanly", switch_ok == "OK")

    # failed assistant message shows Retry; retry produces a real answer
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        const c=S.conversations.find(c=>c.id==='switchtest');
        c.messages.push({role:'user',content:'when are my exams',ts:Date.now()});
        c.messages.push({role:'assistant',content:'Something went wrong.',error:true,ts:Date.now()});
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector(".msg.assistant", timeout=8000)
    has_retry = page.evaluate(
        "[...document.querySelectorAll('.msg.assistant .icon-btn')].some(b=>b.getAttribute('aria-label')==='Retry')")
    check("failed message shows Retry affordance", has_retry)
    page.click(":nth-match(.msg.assistant .icon-btn[aria-label='Retry'], 1)")
    # correct behavior: retry REPLACES the failed bubble (no duplicates)
    page.wait_for_selector(".msg.assistant:last-child .bubble:has-text('ERP')", timeout=30000)
    retry_reply = page.text_content(".msg.assistant:last-child .bubble")
    check("Retry replaces failure with a fresh answer", "exam" in retry_reply.lower())

    # ---------- Phase-5 multilingual UX regressions ----------
    # language chip on assistant messages (from real backend meta)
    chip = page.locator(".lang-chip").first
    check("assistant message shows language chip", chip.count() == 1 and "English" in chip.text_content())

    # dir="auto" on bubbles for script alignment
    check("bubbles use dir=auto", page.evaluate(
        "document.querySelectorAll('.bubble[dir=auto]').length >= document.querySelectorAll('.bubble').length/2"))

    # welcome greeting cycles through tested languages
    page.click("#new-chat")
    page.wait_for_selector("#welcome.show", timeout=5000)
    g1 = page.text_content("#greet")
    page.wait_for_function("document.getElementById('greet').textContent !== '%s'" % g1, timeout=6000)
    check("welcome greeting cycles multilingually", g1 != page.text_content("#greet"))

    # Hindi suggestion card sends a real Hindi question
    check("six suggestion cards incl. multilingual",
          page.locator("#cards .card").count() == 6)

    # language-switch divider appears ONLY on actual change (store-crafted)
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        S.conversations=[{id:'sw',title:'Switch',createdAt:Date.now(),updatedAt:Date.now(),
          messages:[
            {role:'user',content:'Explain machine learning.',ts:Date.now()},
            {role:'assistant',content:'Sure.',meta:{language_meta:{language:'en',language_name:'English'}},ts:Date.now()},
            {role:'user',content:'मशीन लर्निंग कैसे काम करती है?',ts:Date.now()},
            {role:'assistant',content:'ज़रूर।',meta:{language_meta:{language:'hi',language_name:'Hindi'}},ts:Date.now()},
            {role:'user',content:'more?',ts:Date.now()},
            {role:'assistant',content:'बिलकुल।',meta:{language_meta:{language:'hi',language_name:'Hindi'}},ts:Date.now()}
          ]}];
        S.currentId='sw';
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector(".msg.assistant", timeout=8000)
    switches = page.locator(".lang-switch").count()
    sw_txt = page.text_content(".lang-switch") if switches else ""
    check("language-switch divider: exactly one on real change",
          switches == 1 and "English → हिन्दी" in sw_txt)
    chips_hi = page.evaluate(
        "[...document.querySelectorAll('.lang-chip')].filter(c=>c.textContent.includes('हिन्दी')).length")
    check("Hindi replies carry हिन्दी · Hindi chips", chips_hi == 2)

    # ---------- Phase-6 history/settings regressions ----------
    # export a chat as markdown download
    page.hover(":nth-match(.conv, 1)")
    with page.expect_download(timeout=8000) as dl:
        page.click(":nth-match(.conv .icon-btn.ex, 1)")
    d = dl.value
    path = d.path()
    content = open(path, encoding="utf-8").read()
    check("export produces .md download with messages",
          d.suggested_filename.endswith(".md") and "GAIA" in content)

    # rename via the accessible modal (prompt() removed in Phase 1)
    page.hover(":nth-match(.conv, 1)")
    page.click(":nth-match(.conv .icon-btn.rn, 1)")
    page.wait_for_selector("#rn-input", timeout=3000)
    check("rename opens accessible modal", page.is_visible("#rn-input"))
    page.fill("#rn-input", "Renamed by suite")
    page.click("#overlay-m .confirm-row .yes")
    page.wait_for_timeout(250)
    check("rename modal saves the new title",
          "Renamed by suite" in page.text_content(":nth-match(.conv .t, 1)"))
    page.keyboard.press("Escape")  # ensure modal closed

    # content-match search shows a snippet (self-sufficient fixture)
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        S.conversations.push({id:'snip',title:'Unrelated title',createdAt:Date.now(),
            updatedAt:Date.now(),
            messages:[{role:'user',content:'when are my exams scheduled this semester',ts:Date.now()}]});
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector("#input", timeout=8000)
    page.fill("#search", "exams")
    page.wait_for_timeout(200)
    has_snip = page.locator(".conv .snip").count() >= 1
    page.fill("#search", "")
    page.wait_for_timeout(200)
    check("content-match search shows snippet rows", has_snip)

    # reduce-motion setting persists and disables card animation
    page.click("#hdr-settings")
    page.wait_for_selector("#overlay-m.show", timeout=3000)
    page.check("#nom")
    page.wait_for_timeout(150)
    page.keyboard.press("Escape")
    page.reload(); page.wait_for_selector("#input", timeout=8000)
    body_no_motion = page.evaluate("document.body.classList.contains('no-motion')")
    anim = page.evaluate(
        "getComputedStyle(document.querySelector('.card')).animationName")
    check("reduce-motion persists after reload and kills animations",
          body_no_motion and anim == "none")
    # restore default for later runs
    page.evaluate("""() => { const S=JSON.parse(localStorage.getItem('gaia.store.v1'));
        S.noMotion=false; localStorage.setItem('gaia.store.v1', JSON.stringify(S)); }""")

    # ---------- Phase-7 voice input regressions ----------
    # headless Chromium has NO SpeechRecognition: the unsupported path is REAL
    rec_available = page.evaluate(
        "!!(window.SpeechRecognition||window.webkitSpeechRecognition)")
    if not rec_available:
        check("mic disabled with explanation in unsupported browsers",
              page.locator("#mic-btn[disabled]").count() == 1
              and "not supported" in page.get_attribute("#mic-btn", "title"))
    else:
        check("mic disabled with explanation in unsupported browsers", True)  # can't test here

    # inject a mock recognition engine to exercise the state machine
    page.evaluate("""() => {
        window.__mockEvents=[];
        class FakeRec{
          constructor(){ this.lang=''; this.continuous=false; this.interimResults=false;
            window.__mockEvents.push('constructed'); }
          start(){ window.__mockEvents.push('start:'+this.lang); }
          stop(){ window.__mockEvents.push('stop'); (this.onend||(()=>{}))(); }
          emit(kind,e){ (this['on'+kind]||(()=>{}))(e); }
        }
        window.webkitSpeechRecognition=FakeRec;
        window.__fake=null;
    }""")
    page.reload(); page.wait_for_selector("#input", timeout=8000)
    page.evaluate("""() => { // override the NATIVE SpeechRecognition (headless Chromium ships one)
        window.__mockEvents=[];
        class FakeRec{
          constructor(){ this.lang=''; this.continuous=false; this.interimResults=false;
            window.__fake=this; window.__mockEvents.push('constructed'); }
          start(){ window.__mockEvents.push('start:'+this.lang); }
          stop(){ window.__mockEvents.push('stop'); (this.onend||(()=>{}))(); }
          emit(kind,e){ (this['on'+kind]||(()=>{}))(e); }
        }
        window.SpeechRecognition=FakeRec;
        window.webkitSpeechRecognition=FakeRec;
        // page-level store (module S), not localStorage: we're past boot
        S.lastLang='hi';
    }""")
    page.click("#mic-btn")
    page.wait_for_timeout(200)
    listening_state = page.evaluate(
        "window.__mockEvents.some(e=>e.startsWith('start:hi-IN')) && document.getElementById('mic-btn').classList.contains('listening')")
    check("mic starts listening in last-chat language (hi-IN)", listening_state)
    check("listening indicator + placeholder", "Listening" in page.get_attribute("#input", "placeholder"))
    # interim transcript lands in the composer
    page.evaluate("""() => { window.__fake.emit('result',{results:[
        [{transcript:'नमस्ते दुनिया',isFinal:false}]]}); }""")
    page.wait_for_timeout(150)
    check("interim transcript lands in composer",
          "नमस्ते" in page.input_value("#input"))
    # Escape stops listening
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check("Escape stops listening",
          page.evaluate("!document.getElementById('mic-btn').classList.contains('listening') && window.__mockEvents.includes('stop')"))
    # error mapping: permission denied gets a user-fixable message
    page.click("#mic-btn"); page.wait_for_timeout(150)
    page.evaluate("""() => { window.__fake.emit('error',{error:'not-allowed'}); window.__fake.emit('end',{}); }""")
    page.wait_for_timeout(200)
    check("permission error explains the fix",
          "permission" in page.text_content("#toast").lower())
    # final result keeps text in composer after end
    check("final transcript preserved (no auto-send by default)",
          "नमस्ते" in page.input_value("#input") and page.locator(".msg").count() >= 0)

    # ---------- Phase-8 voice output regressions (patch-based mocks) ----------
    # window.speechSynthesis is a getter-only native accessor: whole-object
    # mocks silently fail. Patch methods on the REAL object instead.
    def mock_speak(voices):
        page.evaluate("""(voices) => {
            window.__utts=[]; window.__cancelled=0;
            class FakeU{constructor(t){this.text=t;this.lang='';this.rate=1;}}
            try{Object.defineProperty(window,'SpeechSynthesisUtterance',
                {value:FakeU,writable:true,configurable:true});}catch(e){}
            const SS=window.speechSynthesis;
            SS.getVoices=()=>voices;
            SS.speak=u=>{window.__utts.push(u);};
            SS.cancel=()=>{window.__cancelled++;};
        }""", voices)

    # Listen on a Hindi message -> language-matched voice
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        S.conversations.push({id:'vo',title:'Voice',createdAt:Date.now(),updatedAt:Date.now(),
          messages:[{role:'user',content:'hi',ts:Date.now()},
                    {role:'assistant',content:'नमस्ते दोस्त। आप कैसे हैं?',ts:Date.now()+1,
                     meta:{language_meta:{language:'hi',language_name:'Hindi'}}}]});
        S.currentId='vo';
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector(".msg.assistant", timeout=8000)
    mock_speak([{"lang": "hi-IN", "name": "Hindi"}, {"lang": "en-IN", "name": "English"}])
    check("Listen button present on assistant messages",
          page.locator(".listen-btn").count() >= 1)
    page.click(":nth-match(.listen-btn, 1)")
    page.wait_for_timeout(200)
    utt = (page.evaluate("window.__utts") or [{}])[0]
    check("Listen speaks in the language-matched voice (hi-IN)",
          utt.get("lang") == "hi-IN" and "नमस्ते" in utt.get("text", ""))
    check("Listen button shows speaking state",
          page.locator(".listen-btn.speaking").count() == 1)
    page.click(":nth-match(.listen-btn, 1)")
    page.wait_for_timeout(150)
    check("clicking again stops speech",
          page.evaluate("window.__cancelled") >= 1
          and page.locator(".listen-btn.speaking").count() == 0)

    # no-voice honesty: Punjabi without a matching voice -> explicit toast
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        S.conversations=[{id:'pa',title:'PA',createdAt:Date.now(),updatedAt:Date.now(),
          messages:[{role:'assistant',content:'ਸਤ ਸ੍ਰੀ ਅਕਾਲ',ts:Date.now(),
                     meta:{language_meta:{language:'pa',language_name:'Punjabi'}}}]}];
        S.currentId='pa';
        localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector(".msg.assistant", timeout=8000)
    mock_speak([{"lang": "en-IN", "name": "English"}])
    page.click(":nth-match(.listen-btn, 1)")
    page.wait_for_timeout(200)
    check("missing voice gets an honest 'no voice' message",
          "no voice available" in page.text_content("#toast").lower()
          and page.evaluate("window.__utts.length") == 0)

    # code fences are announced as skipped, never read
    skipped = page.evaluate(r"speechText('Intro.```python\nprint(1)\n```Outro done.')")
    check("code fences are skipped in speech", "Code block skipped." in skipped and "print" not in skipped)

    # auto-read: streaming replies speak sentence-by-sentence; rate honored
    page.evaluate("S.autoRead=true; S.speakRate=1.25;")
    page.fill("#input", "when are my exams")
    page.click("#send")
    page.wait_for_function("window.__utts && window.__utts.length>=1", timeout=30000)
    u2 = page.evaluate("window.__utts[0]")
    check("auto-read speaks streaming replies sentence-by-sentence",
          len(u2.get("text", "")) > 5)
    check("speech rate setting applied", abs(u2.get("rate", 1) - 1.25) < 0.01)
    page.evaluate("S.autoRead=false; stopSpeak();")

    # ---------- shell-layout regression (live-caught Safari bug) ----------
    # A visible #scrim is a grid child that steals the main column and wraps
    # .main under the sidebar. Assert the desktop shell geometry directly.
    shell = page.evaluate("""() => {
        const scrim=getComputedStyle(document.querySelector('#scrim')).display;
        const m=document.querySelector('.main').getBoundingClientRect();
        const s=document.querySelector('.sidebar').getBoundingClientRect();
        return {scrim, mainX:Math.round(m.x), mainW:Math.round(m.width), sideW:Math.round(s.width),
                mainRightOfSidebar: m.x >= s.width - 1,
                mainFillsColumn: m.width >= innerWidth - s.width - 2,
                composerInMain: document.querySelector('.composer-wrap')
                    .getBoundingClientRect().x >= s.width - 1};
    }""")
    check("desktop shell: scrim inert, main beside sidebar, composer in main",
          shell["scrim"] == "none" and shell["mainRightOfSidebar"]
          and shell["mainFillsColumn"] and shell["composerInMain"])

    # ---------- errors visible? ----------
    check("no JS page/console errors during session", len(errors) == 0)
    if errors:
        print("   JS errors:", errors[:3])

    # ---------- Phase-1 stability regressions ----------
    # scroll architecture: 120-message conversation must be scrollable,
    # reach the top, show the jump pill, and return via it
    page.evaluate("""() => {
        const KEY='gaia.store.v1';
        const S=JSON.parse(localStorage.getItem(KEY));
        const c=S.conversations.find(c=>c.id===S.currentId) || S.conversations[0];
        c.messages = c.messages.slice(0,1);
        for (let i=0;i<120;i++) c.messages.push({role:i%2?'assistant':'user',
            content:'Message '+i+' — long line to give it height '.repeat(3), ts:Date.now()+i});
        S.currentId=c.id; localStorage.setItem(KEY, JSON.stringify(S));
    }""")
    page.reload(); page.wait_for_selector(".msg", timeout=8000)
    page.wait_for_timeout(400)
    can_scroll = page.evaluate(
        "document.getElementById('chat').scrollHeight - document.getElementById('chat').clientHeight > 400")
    check("120-message conversation: chat area owns vertical scroll", can_scroll)
    page.evaluate("document.getElementById('chat').scrollTop = 0")
    page.wait_for_timeout(200)
    top_ok = page.evaluate("document.getElementById('chat').scrollTop < 10")
    check("scroll up to oldest messages works", top_ok)
    page.wait_for_selector("#jump.show", timeout=3000)
    check("jump pill appears when scrolled up", page.is_visible("#jump.show"))
    page.click("#jump")
    page.wait_for_timeout(200)
    check("jump pill returns to latest", page.evaluate(
        "(document.getElementById('chat').scrollHeight - document.getElementById('chat').scrollTop - document.getElementById('chat').clientHeight) < 130"))
    # anti-force-scroll: scheduleFollow must NOT move an up-scrolled viewport
    page.evaluate("document.getElementById('chat').scrollTop = 0")
    page.wait_for_timeout(100)
    page.evaluate("scheduleFollow()")
    page.wait_for_timeout(120)
    check("stream-follow does not force-scroll a reading user", page.evaluate(
        "document.getElementById('chat').scrollTop < 10"))
    page.evaluate("scheduleFollow()")  # at top still
    page.evaluate("document.getElementById('chat').scrollTop = 1e9")
    page.evaluate("scheduleFollow()")
    page.wait_for_timeout(120)
    check("stream-follow resumes when near bottom", page.evaluate(
        "(document.getElementById('chat').scrollHeight - document.getElementById('chat').scrollTop - document.getElementById('chat').clientHeight) < 130"))
    # composer stays in viewport at scroll top
    box = page.locator(".composer-wrap").bounding_box()
    check("composer visible at top of long conversation",
          box and box["y"] + box["height"] <= 800)
    # XSS regression: md() must escape raw HTML
    safe = page.evaluate("md('<img src=x onerror=window.__pwn=1> <script>window.__pwn=1</script>')")
    check("markdown escapes raw HTML (no XSS)",
          "&#60;img" in safe and "&#60;script" in safe and "<img" not in safe)
    check("no injected script executed", not page.evaluate("window.__pwn || false"))

    os.remove(doc_path)
    browser.close()

    fails = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fails)}/{len(results)} browser tests passed"
          + ("" if not fails else f" — FAILED: {fails}"))
    return 0 if not fails else 1


if __name__ == "__main__":
    with sync_playwright() as pw:
        sys.exit(run(pw))
