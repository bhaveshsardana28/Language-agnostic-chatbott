"""Code-switching / mixed-language detection regression suite.
Offline (langdetect + lexicons only). Run: venv/bin/python tests/test_code_switching.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detection import detect_meta


def check(text, primary, code_switched=None, mixed_script=None, secondary=None, label=""):
    m = detect_meta(text)
    ok = m["primary_language"] == primary
    if code_switched is not None:
        ok = ok and m["code_switched"] == code_switched
    if mixed_script is not None:
        ok = ok and m["mixed_script"] == mixed_script
    if secondary is not None:
        ok = ok and m["secondary_languages"] == secondary
    status = "PASS" if ok else f"FAIL got={m['primary_language']}/cs={m['code_switched']}/ms={m['mixed_script']}/sec={m['secondary_languages']}"
    print(f"{status:55s} {label or text[:48]}")
    return ok


def main():
    all_ok = True

    print("-- spec cases --")
    all_ok &= check("मुझे नई DESH KI भाषा सीखने में कितना समय लगेगा?",
                    "hi", code_switched=True, mixed_script=True,
                    label="1. DESH KI mixed-script")
    all_ok &= check("मुझे नई भाषा सीखने में कितना समय लगेगा?",
                    "hi", code_switched=False, mixed_script=False,
                    label="2. pure Hindi")
    all_ok &= check("Mujhe new language seekhne mein kitna time lagega?",
                    "hi", code_switched=True, label="3. Hinglish latin")
    all_ok &= check("How long does it take to learn a new language?",
                    "en", code_switched=False, label="4. English")
    all_ok &= check("Was kann ich tun, um meine Sprachkenntnisse zu verbessern?",
                    "de", label="5. German")
    all_ok &= check("मुझे Python सीखना है", "hi", code_switched=False,
                    label="6. Hindi + tech term (no over-correction)")
    all_ok &= check("मैं ChatGPT के बारे में सीखना चाहता हूँ", "hi", code_switched=False,
                    label="7. Hindi + ChatGPT")
    all_ok &= check("मैं Python सीखना चाहता हूँ, but I don't know where to start.",
                    "hi", code_switched=True, secondary=["en"],
                    label="8. Hindi primary + English clause")

    print("-- code-switching, other languages --")
    all_ok &= check("ਮੈਨੂੰ Python ਸਿੱਖਣੀ ਹੈ, ਕਿੱਥੋਂ start ਕਰਾਂ?", "pa", code_switched=True,
                    label="Punjabi + start")
    all_ok &= check("Quiero mejorar my English.", "es", label="Spanish + English words")
    all_ok &= check("Wie kann ich mein English verbessern?", "de", label="German + English word")
    all_ok &= check("Comment améliorer my English?", "fr", label="French + English word")

    print("-- romanized --")
    all_ok &= check("Mujhe Hindi seekhni hai", "hi", label="romanized Hindi")
    all_ok &= check("Main kal Delhi ja raha hoon", "hi", label="romanized Hindi 2")
    all_ok &= check("mujhe python samajh nahi aa raha", "hi", label="romanized + tech")
    all_ok &= check("mujhe python seekhna hai", "hi", code_switched=False,
                    label="romanized, tech only (no code-switch)")

    print("-- over-correction guards --")
    all_ok &= check("Ich lerne Python", "de", label="German + tech")
    all_ok &= check("¿Cómo puedo aprender Python?", "es", label="Spanish + tech")
    all_ok &= check("मेरा Computer खराब है", "hi", label="Hindi + Computer")
    all_ok &= check("The main idea is simple", "en", label="English containing 'main'")

    print("-- pure languages must not regress --")
    for text, lang in [
        ("I would like to know the exam schedule for this semester", "en"),
        ("Wann sind die Prüfungen?", "de"),
        ("¿Cuándo son los exámenes?", "es"),
        ("Quand sont les examens ?", "fr"),
        ("Quando sono gli esami?", "it"),
        ("मिड सेमेस्टर परीक्षाएं कब हैं", "hi"),
        ("ਮੈਂ ਲਾਇਬ੍ਰੇਰੀ ਕਿਵੇਂ ਜੁਆਇਨ ਕਰਾਂ", "pa"),
    ]:
        all_ok &= check(text, lang, label=f"pure {lang}")

    # empty input
    m = detect_meta("")
    empty_ok = m["language"] is None and m["confidence"] == 0.0
    all_ok &= empty_ok
    print(f"{'PASS' if empty_ok else 'FAIL':55s} empty input")

    print("\n" + ("ALL CODE-SWITCHING TESTS PASSED" if all_ok else "FAILURES PRESENT"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
