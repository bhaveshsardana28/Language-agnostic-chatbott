const MOCK_ID = 'mock-phase4-conversation';

const responseFor = message => {
  const lower = message.toLowerCase();
  if (lower.includes('uncertain') || lower.includes('low confidence')) return {
    language_meta: { language: 'en', primary_language: 'en', language_name: 'English', secondary_languages: ['hi'], code_switched: true, mixed_script: true, scripts: { Latin: 0.65, Devanagari: 0.35 }, script: 'Latin + Devanagari', confidence: 0.35, detection_reason: 'fixture: low confidence' },
    route: 'general', reason: 'fixture', response_lang: 'en',
    text: 'I detected more than one language in that message, so please verify the language label in Insights.',
  };
  if (lower.includes('code') || lower.includes('python')) return {
    language_meta: { language: 'en', primary_language: 'en', language_name: 'English', secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latin: 1 }, script: 'Latin', confidence: 0.99, detection_reason: 'fixture' },
    route: 'general', reason: 'fixture', response_lang: 'en',
    text: 'Here is a small, readable starting point:\n\n```python\ndef greet(name):\n    return f"Hello, {name}!"\n```\n\nThe function keeps the data flow visible and easy to change.',
  };
  if (/[\u0900-\u097f]/.test(message)) return {
    language_meta: { language: 'hi', primary_language: 'hi', language_name: 'Hindi', secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Devanagari: 1 }, script: 'Devanagari', confidence: 0.99, detection_reason: 'fixture' },
    route: 'general', reason: 'fixture', response_lang: 'hi',
    text: 'हर दिन थोड़ा-सा अभ्यास एक अच्छी शुरुआत है। पहले उपयोगी वाक्य चुनिए, फिर उन्हें किसी वास्तविक बातचीत में आज़माइए।',
  };
  return {
    language_meta: { language: 'en', primary_language: 'en', language_name: 'English', secondary_languages: [], code_switched: false, mixed_script: false, scripts: { Latin: 1 }, script: 'Latin', confidence: 0.99, detection_reason: 'fixture' },
    route: 'general', reason: 'fixture', response_lang: 'en',
    text: 'Start with a little of it every day. Choose a useful phrase, listen to how it sounds, and use it in a real conversation.\n\n> Small conversations make a good beginning.',
  };
};

const sleep = (ms, signal) => new Promise((resolve, reject) => {
  const timer = setTimeout(resolve, ms);
  signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); }, { once: true });
});

export async function mockStream(message, { signal, onFrame }) {
  const fixture = responseFor(message);
  onFrame({ type: 'meta', conversation_id: MOCK_ID, ...fixture });
  const chunks = fixture.text.match(/.{1,22}(?:\s|$)/g) || [fixture.text];
  for (const chunk of chunks) { await sleep(95, signal); onFrame({ type: 'delta', text: chunk }); }
  await sleep(95, signal);
  onFrame({ type: 'done', latency_ms: chunks.length * 95, model: 'mock fixture', sources: [] });
  return MOCK_ID;
}
