# Aikya (ऐक्य) — 30-Day Implementation Roadmap

> **From "Language-Agnostic Chatbot" to Award-Winning AI Platform**

## Phase 1: Foundation (Days 1–7)
**Theme: Core Architecture & Data Layer**
**Goal: Working scaffold with auth, DB, and basic chat**

| Day | Task | Tech Stack | Deliverable | Acceptance Criteria |
|-----|------|-----------|-------------|---------------------|
| **1** | **Monorepo Setup** | Next.js 14, FastAPI, Docker | Scaffolded project | `docker-compose up` works, hot reload active |
| 1a | Initialize Next.js app | `npx create-next-app@latest` | frontend/ folder | `npm run dev` serves on 3000 |
| 1b | Initialize FastAPI app | `fastapi`, `uvicorn` | backend/ folder | `uvicorn main:app --reload` works |
| 1c | Docker Compose | Docker, docker-compose | `docker-compose.yml` | All services start with one command |
| **2** | **Database Design** | PostgreSQL, Alembic | Schema + migrations | Tables exist in DB |
| 2a | Design ER diagram | dbdiagram.io or DrawSQL | PNG + SQL DDL | All tables from ARCHITECTURE.md |
| 2b | Set up SQLAlchemy models | SQLAlchemy 2.0 (async) | `models.py` | All models defined |
| 2c | Create Alembic migrations | `alembic init` | migration files | `alembic upgrade head` applies cleanly |
| **3** | **Authentication System** | NextAuth.js, JWT, Argon2 | Login, signup, sessions | OAuth + email/password both work |
| 3a | NextAuth config | `next-auth` v5 | `auth.ts` | Google OAuth login works |
| 3b | FastAPI JWT middleware | `python-jose`, `passlib` | `dependencies.py` | Protected routes reject invalid tokens |
| 3c | Password registration | Argon2 hashing | Registration endpoint | Passwords hashed, not stored plain |
| **4** | **API Design** | FastAPI, Pydantic | REST API spec | Swagger UI live at `/docs` |
| 4a | Design API contract | OpenAPI 3.0 | `openapi.yaml` | All endpoints documented |
| 4b | Implement chat endpoints | FastAPI routers | `/api/v1/chat/*` | CRUD for conversations + messages |
| 4c | Implement user endpoints | FastAPI routers | `/api/v1/users/*` | Profile, settings, history |
| **5** | **Frontend Shell** | Next.js, Tailwind, shadcn/ui | Responsive app shell | Sidebar + main area visible |
| 5a | Install shadcn/ui components | `npx shadcn-ui@latest` | UI components | Button, Input, Card, Sheet working |
| 5b | Build sidebar layout | React, Tailwind | `Sidebar.tsx` | Collapsible, responsive |
| 5c | Dark/light mode | `next-themes` | Theme toggle | Persists across page reloads |
| **6** | **Basic Chat UI** | React, Zustand | Chat interface | Messages render, input works |
| 6a | Build message components | React | `MessageBubble.tsx` | User/assistant differentiation |
| 6b | Build chat input | React, `react-textarea-autosize` | `ChatInput.tsx` | Enter sends, Shift+Enter newlines |
| 6c | Connect to API | TanStack Query | `useChat` hook | Messages persist after refresh |
| **7** | **Integration Test** | Playwright | E2E test | Full chat flow works end-to-end |
| 7a | Write test scripts | Playwright | `tests/e2e/chat.spec.ts` | Send message → see response → verify |
| 7b | Deploy to staging | Vercel + Render | Staging URL | Live on internet |

**Phase 1 Milestone:** ✅ Basic chat working with auth, DB, and deployment

---

## Phase 2: Core AI (Days 8–14)
**Theme: Multi-Model Integration & Memory**
**Goal: Intelligent model routing and persistent memory**

| Day | Task | Tech Stack | Deliverable | Acceptance Criteria |
|-----|------|-----------|-------------|---------------------|
| **8** | **Model Router** | Python, FastAPI | Adaptive router | Routes to correct model |
| 8a | Design routing logic | Python | `router.py` | Complexity scoring algorithm |
| 8b | Implement cost estimator | Python | Cost calculator per query | Latency and cost estimates |
| 8c | A/B testing framework | Python | `experiments.py` | Can compare model outputs |
| **9** | **OpenAI + Gemini Integration** | OpenAI SDK, Google GenAI | Cloud LLM support | Both APIs respond correctly |
| 9a | OpenAI integration | `openai` Python SDK | `providers/openai.py` | GPT-4o, GPT-3.5 working |
| 9b | Gemini integration | `google-generativeai` | `providers/gemini.py` | Gemini 1.5 Pro/Flash working |
| 9c | Unified response format | Pydantic models | `schemas/llm.py` | All providers return same format |
| **10** | **Ollama Local Model** | Ollama, Docker | Offline mode | Works without internet |
| 10a | Ollama integration | `requests` to local API | `providers/ollama.py` | Llama 3.1 responds |
| 10b | Model management UI | React | Model selector dropdown | User can switch between local models |
| 10c | Fallback logic | Python | Auto-fallback | Falls back to local if cloud fails |
| **11** | **Claude + Codex Integration** | Anthropic SDK, OpenAI | All 5 providers working | Complete multi-model dashboard |
| 11a | Claude integration | `anthropic` SDK | `providers/claude.py` | Claude 3.5 working |
| 11b | Codex integration | OpenAI Completion API | `providers/codex.py` | Code generation working |
| 11c | Model comparison UI | React | Side-by-side view | Can compare 2+ model responses |
| **12** | **Short-Term Memory** | Redis, Python | Context window mgmt | Last 10 messages remembered |
| 12a | Context window algorithm | Python | Sliding window + summarization | No token overflow |
| 12b | Redis session cache | `redis-py` | Session messages in Redis | <10ms retrieval |
| 12c | Conversation starter | Python | Auto-title generation | First message → auto-title |
| **13** | **Vector Database** | Pinecone, `langchain` | Semantic search | Can find similar past messages |
| 13a | Set up Pinecone index | Pinecone console | Vector index | Embeddings store and retrieve |
| 13b | Message embedding pipeline | `langchain`, `openai-embeddings` | Embed on message save | Async embedding background task |
| 13c | Semantic search endpoint | FastAPI | `/api/v1/search` | Returns semantically similar messages |
| **14** | **Memory Graph** | NetworkX or Neo4j | Knowledge graph | Facts extracted and linked |
| 14a | NER extraction | spaCy or GPT | Entity extractor | Identifies people, places, concepts |
| 14b | Fact storage | PostgreSQL + Pinecone | `memory` table + vectors | Facts persist across conversations |
| 14c | Memory recall | Python | Context injection | Relevant facts added to system prompt |

**Phase 2 Milestone:** ✅ Multi-model routing + persistent memory working

---

## Phase 3: Advanced Features (Days 15–21)
**Theme: Voice, Documents, Web, Agents**
**Goal: Feature parity with top AI platforms**

| Day | Task | Tech Stack | Deliverable | Acceptance Criteria |
|-----|------|-----------|-------------|---------------------|
| **15** | **Voice Input** | Whisper, Web Audio API | Microphone input | Real-time transcription |
| 15a | Web Audio API integration | Browser API | `VoiceRecorder.tsx` | Records audio in browser |
| 15b | Whisper API integration | OpenAI Whisper | `providers/whisper.py` | Audio → text with high accuracy |
| 15c | Voice visualization | Canvas/WaveSurfer.js | Waveform display | Real-time waveform during recording |
| **16** | **Voice Output** | Coqui TTS, Web Speech API | Natural speech | Multiple voice options |
| 16a | TTS API integration | `pyttsx3` or Coqui | `providers/tts.py` | Text → audio file |
| 16b | Playback UI | HTML5 Audio | Audio player in chat | Play/pause/speed controls |
| 16c | Voice selection | React | Voice picker | Accents, languages, speed |
| **17** | **Document Upload + RAG** | PyPDF, LangChain, Pinecone | PDF chat | Chat with uploaded documents |
| 17a | File upload handling | Multer, S3/R2 | Upload endpoint | PDF, DOCX, TXT accepted |
| 17b | Document parsing | `pypdf`, `docx2txt` | Text extraction | Preserves structure, handles images |
| 17c | Chunking + embedding | LangChain | `document_processor.py` | Smart chunking, overlap handling |
| 17d | RAG retrieval | Pinecone + LangChain | Context injection | Relevant chunks added to prompt |
| 17e | Source highlighting | React | Inline citations | Click to jump to source in PDF |
| **18** | **Web Search + Citations** | Tavily, Serper | Real-time web answers | Perplexity-style with sources |
| 18a | Web search integration | Tavily API | `providers/web_search.py` | Returns top-5 results with snippets |
| 18b | Web page scraping | `trafilatura` | Content extraction | Clean text extraction |
| 18c | Answer synthesis | LLM + RAG | Synthesized response | Combines multiple sources into answer |
| 18d | Citation UI | React | Numbered citations | Clickable, source verification |
| **19** | **Code Execution** | Sandboxed Docker, FastAPI | Run code in chat | Supports 50+ languages |
| 19a | Code block detection | Regex + AST | Language classifier | Identifies code blocks |
| 19b | Sandboxed execution | Docker container | `code_runner.py` | Isolated, timed, safe |
| 19c | Output rendering | React | Terminal-style output | Stdout, stderr, timing |
| **20** | **AI Agent Workflows** | LangGraph, LangChain | Multi-step automation | Research → Summarize → Create |
| 20a | Agent architecture | LangGraph | `agents/` module | ReAct, Plan-and-execute patterns |
| 20b | Tool definitions | Python functions | `tools/web_search.py`, etc. | 5+ tools available to agents |
| 20c | Workflow templates | YAML/JSON | Preset workflows | "Research Paper", "Travel Planner" |
| 20d | Progress UI | React | Step-by-step progress | User sees agent thinking steps |
| **21** | **Image Understanding** | GPT-4V, Gemini Vision | Multimodal chat | Upload image + ask questions |
| 21a | Image upload handling | Multer, S3 | Image upload endpoint | PNG, JPG, WebP support |
| 21b | Vision model integration | GPT-4V API | `providers/vision.py` | Image → description |
| 21c | Gallery UI | React | Image grid + lightbox | Browse uploaded images |
| 21d | OCR integration | Tesseract / GPT-4V | Text extraction from images | Handwriting support |

**Phase 3 Milestone:** ✅ Voice, documents, web search, agents, and vision working

---

## Phase 4: Collaboration & Enterprise (Days 22–26)
**Theme: Teams, Sharing, Analytics**
**Goal: Production-ready for teams and businesses**

| Day | Task | Tech Stack | Deliverable | Acceptance Criteria |
|-----|------|-----------|-------------|---------------------|
| **22** | **Team Workspaces** | PostgreSQL, Next.js | Create/join teams | Team dashboard, member list |
| 22a | Team CRUD | FastAPI | Team endpoints | Create, update, delete teams |
| 22b | Team switcher | React | Dropdown in sidebar | Switch between personal/team context |
| 22c | Team settings | React | Settings page | Name, logo, description |
| **23** | **Role-Based Access** | PostgreSQL, CASL | Admin/Editor/Viewer | Permission enforcement |
| 23a | Permission system | CASL or custom | `permissions.py` | 3-tier role checking |
| 23b | UI adaptation | React | Conditional rendering | Editors see "Edit", viewers don't |
| 23c | API enforcement | FastAPI middleware | `@require_role` decorator | Backend rejects unauthorized |
| **24** | **Chat Sharing** | UUID tokens, React | Public/private links | Share any conversation |
| 24a | Share token generation | Python | `share_token` field | Unique, unguessable tokens |
| 24b | Public view | Next.js (SSR) | `/s/[token]` page | Read-only, no login required |
| 24c | Embedding | iframe | Embed code | Copy-paste into blog/website |
| 24d | QR code | `qrcode` library | QR generation | Mobile-friendly sharing |
| **25** | **Analytics Dashboard** | PostgreSQL, Recharts | Usage insights | Charts, metrics, exports |
| 25a | Aggregation pipeline | SQL + Python | Daily aggregation job | cron or Celery beat |
| 25b | Dashboard UI | Recharts, React | `/dashboard` page | Time-series, pie charts |
| 25c | Export reports | `xlsx`, `csv` | Download reports | Monthly usage PDF |
| **26** | **API Access** | FastAPI, JWT | Programmatic API | Scoped keys for developers |
| 26a | API key generation | UUID, hashing | `/api/v1/keys` endpoint | Scoped read/write keys |
| 26b | API documentation | Swagger + examples | Developer portal | Rate limits, examples, SDK |
| 26c | Postman collection | JSON | `Aikya_API.postman_collection` | One-click import |

**Phase 4 Milestone:** ✅ Team collaboration and analytics ready

---

## Phase 5: Polish & Launch (Days 27–30)
**Theme: Performance, Testing, Launch**
**Goal: Production-grade platform ready for users**

| Day | Task | Tech Stack | Deliverable | Acceptance Criteria |
|-----|------|-----------|-------------|---------------------|
| **27** | **Performance Optimization** | Redis, CDN, lazy loading | < 300ms TTFB | Lighthouse score > 90 |
| 27a | Frontend optimization | Next.js features | Code splitting, lazy loading | Bundle size < 500KB initial |
| 27b | Backend optimization | FastAPI | Connection pooling, async DB | P95 latency < 500ms |
| 27c | Caching strategy | Redis | Query result caching | Cache hit rate > 80% |
| 27d | CDN setup | Cloudflare/Vercel Edge | Static asset caching | Global TTFB < 200ms |
| **28** | **Comprehensive Testing** | Pytest, Playwright, k6 | Test suite | > 80% coverage |
| 28a | Unit tests | Pytest | `tests/unit/` | All services covered |
| 28b | Integration tests | Pytest | `tests/integration/` | API contract validation |
| 28c | E2E tests | Playwright | `tests/e2e/` | Critical user flows |
| 28d | Load testing | k6 | `tests/load/` | Handles 1000 concurrent users |
| **29** | **Documentation + Demo** | Markdown, videos | Complete package | README, docs, video |
| 29a | README | Markdown | `README.md` | Clear setup, features, screenshots |
| 29b | Architecture docs | Markdown | `docs/` | API docs, deployment guide |
| 29c | Demo video | Screen recording | `demo.mp4` | 3-minute walkthrough |
| 29d | Presentation deck | Google Slides/PPT | `pitch.pptx` | 10-slide pitch for judges |
| **30** | **Production Deployment** | Vercel, AWS, domain | Live platform | Custom domain, SSL, monitoring |
| 30a | Production build | Docker | Optimized images | No dev dependencies |
| 30b | Domain setup | Namecheap/Cloudflare | Custom domain | `aikya-ai.vercel.app` or custom |
| 30c | SSL + Security | Let's Encrypt, WAF | HTTPS only | A+ SSL rating |
| 30d | Monitoring | Sentry, Grafana | Alerting setup | Error tracking, uptime alerts |
| 30e | Soft launch | Social media | Beta signup | 100+ beta users |

**Phase 5 Milestone:** ✅ Production deployment, live platform!

---

## Daily Checkpoints

Every day at the end of coding, verify:
- [ ] Code compiles without errors
- [ ] Tests pass (even if just basic ones)
- [ ] Features from that day are demo-able
- [ ] Commit to Git with meaningful messages
- [ ] Update this ROADMAP with ✅/❌ status

## Weekly Reviews

| Week | Review Focus | Deliverable |
|------|-------------|-------------|
| Week 1 | Foundation & Auth | Working login + basic chat |
| Week 2 | AI Integration | Multi-model chat with memory |
| Week 3 | Advanced Features | Voice, docs, web search, agents |
| Week 4 | Collaboration & Launch | Teams, analytics, live deployment |

## Resource Links

- **Architecture Document**: `docs/ARCHITECTURE.md`
- **Database Schema**: See Section E in ARCHITECTURE.md
- **API Documentation**: `http://localhost:8000/docs` (when backend running)
- **Staging URL**: [To be deployed]
- **Production URL**: [To be deployed]

---

*"The only way to do great work is to love what you do." — Steve Jobs*

*Let's build something incredible.* 🚀
