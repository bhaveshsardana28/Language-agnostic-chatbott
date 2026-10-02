# Demo script (5–7 minutes). Practise ×3 in buffer week. Phone-hotspot the laptop so venue Wi-Fi can't hurt you; the disk cache means repeated demo questions won't re-hit the network.

0. **Before the panel sits down:** `./venv/bin/python app.py` running,
   browser open on http://localhost:5000, `results/confusion_matrix.png`
   open in a second tab, `logs/app.log` being tailed in a terminal below.

1. **(30 s) English sanity.** Type: `when is my next class`
   → reply + badge `en · intent: timetable`. Point at the badge:
   "detection, intent and confidence are all visible in the UI".

2. **(60 s) The pivot, live.** Type in Hindi: `मेरी फीस कब तक भरनी है`
   → Hindi reply, badge `hi · intent: fees`. Then Punjabi: `ਲਾਇਬ੍ਰੇਰੀ ਕਿੰਨੇ ਵਜੇ ਖੁੱਲ੍ਹਦੀ ਹੈ`
   → Punjabi reply, badge `pa · intent: library`.
   Say: "No Hindi model. No Punjabi model. One English model; translation does the rest."

3. **(60 s) Graceful failure, on purpose.** Type nonsense: `asdf qwerty zxcv`
   → polite localized fallback, badge shows `fallback`. Say: "Below a measured
   confidence threshold the system declines instead of guessing — threshold
   was tuned on out-of-fold data, not guessed."

4. **(60 s) Show the evidence.** Tab to confusion matrix → "English CV
   accuracy 0.80, macro F1 0.81". Show REPORT §5.4 table → pivot vs
   no-pivot baseline: "without translation the same model is 4–14× worse".

5. **(60 s) The headline extensibility claim.** Open `config.py`, add Italian
   (already shown added in Phase 7 — demonstrate by commenting in/out):
   type `quando sono gli esami?` → Italian reply, badge `it · intent: exam_schedule`.
   Say: "That language was never trained on. One config line. That is the thesis."

6. **(30 s) Honest limitation, unprompted.** Type Hinglish:
   `mera result kab aayega` → whatever happens, narrate: "code-mixed text is
   our documented limitation; detection may mis-route; it's in the report with
   a measured detection-accuracy table." Panels love self-awareness.

**Demo-day failure drills:** translation down → replies degrade to English
with the fallback badge; say "the provider is rate-limiting us; the system
degrades gracefully by design" — that IS the feature. Total translation
outage: demo English + show results/ tables.
