# Document QA/RAG diagnosis

**Investigated 13 October 2026.** The reported fallback was reproduced against
the FastAPI V2 pipeline with a deterministic Aurora fixture. The failure was not
the V2 frontend: upload returned 200, extraction/indexing completed, the same
conversation ID was used, and the SSE `retrieval-gate` response was rendered
faithfully.

## Confirmed root causes

1. **The retrieval gate was applied to broad document operations.** Questions such
   as “What is in this document?” and “Summarize the uploaded document.” were sent
   through the same single-query similarity threshold as precise factual QA. Their
   generic wording produced low similarity and returned before the LLM was called.
2. **Explicit document intent lost to other routes.** A question containing words
   such as `2026`, `current` or `exam` could be routed to web/campus before the
   uploaded-document route. The router now prioritizes explicit document language
   when the active conversation has documents.
3. **The document system prompt was not actually sent.** `main.py` constructed the
   generic `messages[0]` before replacing the local `sys_prompt` with the
   document-specific instruction. The provider therefore received the generic
   prompt plus excerpts, not the grounded document prompt.
4. **Context was truncated to 600 characters per chunk.** Relevant facts later in a
   valid chunk could disappear before prompt construction. Context is now bounded
   by a total character budget while preserving complete normal chunks.
5. **Keyword fallback reused the embedding threshold.** The degraded lexical scorer
   produces smaller Jaccard-like values than cosine similarity. It now has its own
   calibrated gate instead of requiring 0.45.
6. **Ingestion was not atomic.** Text and metadata were appended before embedding
   succeeded, and a later embedding failure could leave a partially indexed
   session. Embeddings are now calculated and dimension-checked before commit.

## Pipeline after the fix

```text
V2 multipart upload
  -> extension/size validation
  -> PDF/DOCX/TXT/MD extraction
  -> PDF page markers + DOCX table text
  -> 1,200-char / 150-overlap chunks
  -> normalized multilingual embeddings (or explicit degraded lexical mode)
  -> atomic per-conversation SQLite commit + lazy in-memory matrix cache
  -> explicit document router precedence
  -> factual threshold or broad overview sampling
  -> bounded context with document/page metadata
  -> document-specific grounded system prompt
  -> LLM SSE deltas + done.sources
  -> V2 source cards/history
```

The current backend uses SQLite for durable conversations, document text,
metadata and serialized float32 embeddings. Retrieval rebuilds a per-session
NumPy matrix lazily after restart; this avoids requiring a vector service while
remaining appropriate for a local single-node corpus. Browser workspaces are
scoped by an `HttpOnly` cookie, but that cookie is not user authentication.
Scanned PDFs use an optional PyMuPDF/Pillow/Tesseract fallback when installed;
otherwise image-only uploads fail explicitly instead of being indexed as empty
text.

## Verification evidence

The deterministic regression fixture contains:

```text
Project Aurora has 42 employees. Its headquarters are in Jaipur.
The internal project code is AURORA-731.
```

The new test proves broad summary context reaches the LLM, precise code retrieval,
unsupported-question refusal before generation, PDF page metadata, DOCX table
extraction, multiple-document ranking, conversation isolation, empty/invalid
uploads, and atomic rollback after embedding failure.

An additional offline end-to-end probe used the cached production MiniLM model and
a stubbed generator:

```text
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./venv/bin/python <probe>
upload_status 200 embeddings True
overview_route document overview_model groq:qwen/qwen3.8-27b llm_calls 2
specific_source_count 1 specific_reply_has_code True
```

The provider name in that output is the configured model label; generation itself
was stubbed, so no external LLM request was made.

Run:

```text
python -m pytest -q tests/test_rag_qa.py tests/test_persistence.py
7 passed
```

The existing `tests/test_v2.py` and full pytest suite remain regression coverage;
their fake embedding gate is intentionally not used as evidence for real embedding
quality. Run `python scripts/eval_rag_multilingual.py --json` for the deterministic
10-case cross-lingual retrieval benchmark; it reports whether the cached
production model or keyword fallback was used.
