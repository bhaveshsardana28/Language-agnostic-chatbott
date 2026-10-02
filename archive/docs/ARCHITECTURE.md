# Aikya (ऐक्य) — Universal AI Assistant
## Software Architecture & Innovation Strategy Document
### Version 2.0 — Grand Finale Edition

---

## A. PROJECT REBRANDING

### New Project Name
**Aikya (ऐक्य) — The Universal AI Assistant**

*Aikya* is derived from Sanskrit, meaning **"Unity"** or **"Oneness."** It represents our vision of unifying human communication across all languages, modalities, and cultural contexts through the power of artificial intelligence.

### Unique Selling Proposition (USP)
> *"The world's first student-built, context-aware polyglot AI that doesn't just translate words—it understands intent, culture, and nuance across 100+ languages while orchestrating multiple AI models in real-time."*

Unlike conventional chatbots that break conversation flow by routing to translation APIs, Aikya maintains **semantic context** across language switches, understands **cultural idioms**, and **auto-selects the best AI model** for each query type (creative, technical, coding, reasoning).

### Problem Statement

**The Global Language Divide in AI:**
1. **78% of internet content is in English**, yet **only 20% of the world speaks it natively**—locking billions out of the AI revolution.
2. Current "multilingual" chatbots translate *after* reasoning, destroying nuance, humor, idioms, and cultural context.
3. Students and professionals in non-English regions face a **10-50x higher cost** for AI tools due to lack of localized alternatives.
4. No existing student project demonstrates **true polyglot AI** with multi-model orchestration, voice interaction, and document intelligence.

### Innovation Highlights

| # | Innovation | Why It's Unique |
|---|---|---|
| 1 | **Contextual Polyglot Engine** | Maintains conversation context across language switches without re-translating history |
| 2 | **Adaptive Model Router** | Auto-selects best model (GPT-4, Claude, Gemini, Local LLaMA) based on query complexity |
| 3 | **Memory Graph** | Builds persistent knowledge graphs from conversations for long-term recall
| 4 | **Voice-Native Architecture** | Native voice input/output with real-time streaming across all languages |
| 5 | **Document Intelligence** | Chat with PDFs/DOCS in any language with source citation |
| 6 | **AI Agent Workflows** | Multi-step tasks: research → summarize → translate → create presentation |
| 7 | **Cultural Context Awareness** | Adapts tone, idioms, and formality based on user's cultural context |
| 8 | **Real-time Web Search + AI** | Perplexity-style answer synthesis with live web sources |

---

## B. COMPLETE ARCHITECTURE

### B.1 Frontend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NEXT.JS 14 (APP ROUTER)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │   / (Home)   │  │ /c/[chatId]  │  │   /settings, /team │ │
│  │  Landing     │  │  Chat Room   │  │   Dashboard, etc.  │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐│
│  │              SHARED COMPONENTS                          ││
│  │  Sidebar │ ChatInput │ MessageBubble │ CodeBlock      ││
│  │  ModelSelector │ VoiceRecorder │ FileUploader        ││
│  └───────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
               ┌────────────────────┐
               │   ZUSTAND STATE  │  (Global: auth, theme, chat)
               │   TANSTACK QUERY │  (Server state, caching)
               │   FRAMER MOTION  │  (Animations, transitions)
               └────────────────────┘
                          │
                          ▼
               ┌────────────────────┐
               │   TAILWIND CSS +   │
               │   SHADCN/UI        │  (Premium UI components)
               └────────────────────┘
```

**Key Frontend Modules:**
- **App Shell**: Persistent sidebar, top navigation, and chat container
- **Chat Interface**: Message streaming, rich content (code, images, tables)
- **Voice UI**: Waveform visualization, real-time transcription feedback
- **Document Viewer**: Inline PDF rendering with highlighted source citations
- **Settings Panel**: Model preferences, language defaults, memory management

---

### B.2 Backend Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI (PYTHON)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  /api/auth   │  │ /api/chat    │  │  /api/memory        │  │
│  │  /api/users  │  │ /api/stream  │  │  /api/agents        │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MIDDLEWARE & SERVICES                        │  │
│  │  JWT Auth │ Rate Limiter │ Request Logger │ Error Handler│  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     AI ORCHESTRATION LAYER                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              LANGGRAPH (Orchestration)                  │ │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐ ┌─────────┐  │ │
│  │   │ Intent  │→ │ Router  │→ │ Memory  │ │ Agent   │  │ │
│  │   │ Classify│  │ Select  │  │ Graph   │ │ Workflow│  │ │
│  │   └─────────┘  └─────────┘  └─────────┘ └─────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ ┌──────────┐│
│  │   OpenAI   │  │   Claude   │  │   Gemini   │ │ Local   ││
│  │   Router   │  │   Router   │  │   Router   │ │ Ollama  ││
│  └────────────┘  └────────────┘  └────────────┘ └──────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Backend Services:**
- **API Gateway**: FastAPI with async endpoints, OpenAPI (Swagger) docs
- **AI Orchestrator**: LangGraph for complex multi-step reasoning and agent workflows
- **Model Router**: Intelligent routing based on query complexity, latency, and cost
- **Memory Service**: Vector storage with semantic search (Pinecone/Milvus)
- **File Service**: Document parsing (PDF, DOCX, TXT), chunking, embedding
- **Voice Service**: Real-time STT (Whisper) + TTS (Piper/Coqui)
- **Web Search**: Serper/Tavily API integration with RAG

---

### B.3 Database Architecture

**PostgreSQL (Primary Database)**
- **Users**: Profile, preferences, subscription, auth
- **Conversations**: Metadata, sharing settings, access control
- **Messages**: Content, tokens, model used, latency, citations
- **Files**: Metadata, vector chunks, upload history
- **Teams**: Collaboration, role-based access

**Redis (Cache & Real-time)**
- Session tokens, rate-limit counters
- Chat streaming state, typing indicators
- Leaderboard, hot topics

**Pinecone / Milvus (Vector Database)**
- Conversation memory embeddings
- Document chunks for RAG
- User preference embeddings

**SQLite → PostgreSQL Migration Guide:**
We will maintain backward compatibility with the current SQLite schema while offering a seamless migration to PostgreSQL for production.

---

### B.4 AI Orchestration Layer

```
┌────────────────────────────────────────────────────────────┐
│               AI ORCHESTRATION PIPELINE                      │
└────────────────────────────────────────────────────────────┘

USER INPUT
    │
    ▼
┌──────────────────┐
│ INTENT CLASSIFIER│  →  [Chat, Code, Research, Document, Image, Voice]
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ LANGUAGE DETECT  │  →  ISO-639 code + confidence score
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ COMPLEXITY SCORE │  →  Simple (local) / Medium (cloud) / Complex (multi-model)
└──────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│                     MODEL ROUTER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Simple Query │  │ Medium Query │  │ Complex Query    │   │
│  │ → Ollama     │  │ → Gemini     │  │ → GPT-4 / Claude │   │
│  │   (Free)     │  │   (Cheap)    │  │   (Accurate)     │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────┐
│ RESPONSE MERGER  │  →  Best-of-N aggregation for complex queries
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ OUTPUT FORMATTER │  →  JSON/Markdown with citations, code blocks, images
└──────────────────┘
```

---

### B.5 Authentication System

| Feature | Implementation |
|---------|----------------|
| **OAuth 2.0** | Google, GitHub, Microsoft login |
| **Email/Password** | Argon2 hashing, email verification |
| **JWT Tokens** | Access + Refresh token pattern, Secure, HttpOnly cookies |
| **Role-Based Access** | `free`, `pro`, `enterprise`, `administration` |
| **API Keys** | Scoped keys for programmatic access (Tradesman pattern) |
| **Audit Log** | Every login, key generation, and permission change logged |

---

### B.6 Conversation Memory System

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────┘

SHORT-TERM (Session)
  → Redis cache of last 10 messages
  → Context window management for LLMs

MEDIUM-TERM (Conversation)
  → PostgreSQL full message history
  → Conversation summary (LLM-generated TL;DR)

LONG-TERM (Knowledge Graph)
  → Vector embeddings of important facts
  → Named Entity Recognition (NER) extraction
  → User preference learning (tone, style, topics)
  → Semantic search across all past conversations
```

**Memory Operations:**
- **Store**: Automatic extraction of facts, preferences, and decisions
- **Retrieve**: Semantic search + keyword search hybrid
- **Update**: Confidence-based fact updating (newer info overrides older)
- **Forget**: GDPR-compliant data deletion, selective memory wipe

---

### B.7 Analytics System

| Metric | Source | Dashboard |
|--------|--------|-----------|
| **Query Volume** | API logs | Time-series chart |
| **Model Usage** | Request metadata | Pie chart (cost breakdown) |
| **Latency** | Timing middleware | P50/P95/P99 histograms |
| **User Retention** | Auth events | Cohort analysis |
| **Language Distribution** | Language detection | World heatmap |
| **Error Rates** | Exception tracking | Alert thresholds |
| **Token Consumption** | Model responses | Daily/weekly/monthly |

---

### B.8 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         PRODUCTION                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Cloudflare │    │   Vercel     │    │   AWS/GCP    │   │
│  │   (CDN/DDoS) │    │   (Frontend) │    │   (Backend)  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │          │
│         └───────────────────┴───────────────────┘          │
│                             │                                │
│                    ┌──────────────────┐                       │
│                    │  Load Balancer   │                       │
│                    └────────┬──────────┘                       │
│          ┌────────────────┬────────────────┐                  │
│   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐       │
│   │ FastAPI     │  │ FastAPI     │  │ FastAPI     │       │
│   │ Instance 1  │  │ Instance 2  │  │ Instance 3  │       │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│          │                │                │              │
│          └────────────────┴────────────────┘              │
│                             │                            │
│                    ┌──────────────────┐                   │
│                    │  Managed DB       │                   │
│                    │  PostgreSQL +     │                   │
│                    │  Redis + Pinecone │                   │
│                    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## C. ADVANCED FEATURES

### C.1 Core Chat Experience

| Feature | Description | Innovation |
|---------|-------------|------------|
| **Multi-Chat Sessions** | Unlimited parallel conversations | Each with independent memory |
| **ChatGPT-Style Sidebar** | Collapsible, searchable, categorized | Auto-categorization by topic |
| **Rename/Delete/Archive** | Full CRUD + soft delete for recovery | 30-day recovery period |
| **Share Chats** | Public/private links, embeddable | QR code generation |
| **Conversation Search** | Full-text + semantic search | Search across ALL history |
| **Export** | PDF, Markdown, JSON, Word | Formatted with citations |

### C.2 AI Capabilities

| Feature | Description | Innovation |
|---------|-------------|------------|
| **Multi-Model Routing** | Auto-select optimal model per query | Latency vs. accuracy trade-off |
| **Model Comparison** | Side-by-side responses from 2+ models | "Ask 3 models" feature |
| **Document Upload** | PDF, DOCX, TXT, CSV | Native RAG with source highlighting |
| **Voice Input** | Real-time streaming STT (Whisper) | 100+ languages, offline capable |
| **Voice Output** | Natural TTS with accent selection | Regional accent matching |
| **Web Search** | Real-time search + AI synthesis | Perplexity-style with citations |
| **Citations** | Every claim backed by source | Auto-extract from web/docs |
| **Code Generation** | Syntax highlighting, execution, debugging | 50+ languages |
| **Image Understanding** | Vision models (GPT-4V, Gemini Vision) | Descriptions, OCR, analysis |
| **Multi-Language** | Native response in 100+ languages | Cultural context adaptation |
| **AI Agent Workflows** | Multi-step tasks with tool use | Auto-prompt generation |

### C.3 Collaboration & Enterprise

| Feature | Description |
|---------|-------------|
| **Team Workspaces** | Shared conversations, templates, models |
| **Role Management** | Admin, Editor, Viewer roles |
| **Team Analytics** | Usage, cost, and engagement dashboard |
| **API Access** | REST + WebSocket APIs for integration |
| **Custom Model Training** | Fine-tune on team's domain data |
| **SSO Integration** | SAML 2.0, OIDC for enterprise |
| **Audit Logs** | Complete activity trail |
| **Data Residency** | Choose region for data storage |

---

## D. UI/UX DESIGN SPECIFICATIONS

### D.1 Design Philosophy
**"Effortless Intelligence"** — Every interaction should feel instantaneous, intuitive, and intelligent.

### D.2 Color Palette
```css
:root {
  --primary: #6366f1;       /* Indigo 500 */
  --primary-hover: #4f46e5; /* Indigo 600 */
  --accent: #10b981;        /* Emerald 500 */
  --background: #0f172a;    /* Slate 900 */
  --surface: #1e293b;       /* Slate 800 */
  --surface-light: #334155; /* Slate 700 */
  --text-primary: #f8fafc;  /* Slate 50 */
  --text-secondary: #94a3b8;/* Slate 400 */
  --border: #334155;        /* Slate 700 */
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
}
```

### D.3 Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ NAV BAR (32px) - Logo, Model Selector, Profile, Settings  │
├─────────────────────────────────────────────────────────────┤
│          │                                                  │
│ SIDEBAR  │              CHAT AREA                           │
│ (280px)  │                                                  │
│          │  ┌───────────────────────────────────────────┐   │
│ Search   │  │           Welcome Screen                   │   │
│ ──────   │  │   (or) Message History                     │   │
│ Chat 1   │  │                                            │   │
│ Chat 2   │  │  ┌─────┐  ┌─────┐  ┌─────┐               │   │
│ Chat 3   │  │  │ User│  │ User│  │ AI  │               │   │
│ ...      │  │  │     │  │     │  │     │               │   │
│          │  │  └─────┘  └─────┘  └─────┘               │   │
│ ──────   │  │                                            │   │
│ New Chat │  │                                            │   │
│ Settings │  └───────────────────────────────────────────┘   │
│          │                                                  │
│          │  ┌───────────────────────────────────────────┐   │
│          │  │  Input: [Text...........................] │   │
│          │  │  [📎] [🎤] [⬆️ Send]                     │   │
│          │  └───────────────────────────────────────────┘   │
└──────────┴─────────────────────────────────────────────────┘
```

### D.4 Responsive Breakpoints
| Breakpoint | Width | Layout |
|---|---|---|
| Mobile | < 640px | Full-width chat, sidebar as drawer |
| Tablet | 640-1024px | Collapsible sidebar |
| Desktop | > 1024px | Fixed sidebar, centered chat |

### D.5 Dark/Light Mode
- System preference detection
- Manual toggle in settings
- Per-user persistent preference
- Smooth CSS transition between modes

---

## E. DATABASE SCHEMA

### E.1 Entity Relationship Diagram

```
┌──────────┐       ┌──────────────┐       ┌──────────┐
│  USERS   │       │ CONVERSATIONS│       │ TEAMS    │
├──────────┤       ├──────────────┤       ├──────────┤
│ id (PK)  │◄─────│ id (PK)      │       │ id (PK)  │
│ email    │       │ user_id (FK) │       │ name     │
│ name     │       │ team_id (FK) │◄─────│ owner_id │
│ avatar   │       │ title        │       └──────────┘
│ created  │       │ created_at   │            │
│ tier     │       │ updated_at   │            │
└──────────┘       │ is_archived  │      ┌───────┘
      │            │ is_shared    │      │
      │            │ share_token  │◄─────┘
      │            └──────────────┘
      │                   │
      │            ┌──────┘
      │            │
      │     ┌──────────┐
      │     │ MESSAGES │
      │     ├──────────┤
      │     │ id (PK)  │
      │     │ conv_id  │
      │     │ role     │
      │     │ content  │
      │     │ tokens   │
      │     │ model    │
      │     │ latency  │
      │     │ created  │
      │     └──────────┘
      │
┌─────┴──────┐
│   FILES    │
├────────────┤
│ id (PK)    │
│ user_id    │
│ conv_id    │
│ filename   │
│ file_type  │
│ file_size  │
│ embedding  │  → Vector (Pinecone)
│ chunks     │  → JSON array
└────────────┘

┌────────────┐
│   MEMORY   │
├────────────┤
│ id (PK)    │
│ user_id    │
│ fact_type  │
│ fact       │
│ embedding  │  → Vector (Pinecone)
│ confidence │
│ source     │
│ created    │
└────────────┘

┌────────────┐
│  SETTINGS  │
├────────────┤
│ user_id    │
│ theme      │
│ language   │
│ default_model│
│ voice_enabled│
│ auto_send  │
└────────────┘
```

### E.2 PostgreSQL Schema (SQL DDL)

```sql
-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    tier VARCHAR(30) DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations Table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID, -- nullable for personal chats
    title VARCHAR(255) DEFAULT 'New Conversation',
    summary TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    is_shared BOOLEAN DEFAULT FALSE,
    share_token UUID UNIQUE DEFAULT gen_random_uuid(),
    language VARCHAR(10) DEFAULT 'auto',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER,
    citations JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Files Table
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory (Knowledge Graph) Table
CREATE TABLE memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    fact_type VARCHAR(50) NOT NULL, -- 'preference', 'fact', 'entity'
    fact TEXT NOT NULL,
    source_conversation_id UUID,
    confidence FLOAT DEFAULT 1.0,
    embedding_vector_id VARCHAR(255), -- References Pinecone/Milvus
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE -- TTL for temporary facts
);

-- Settings Table
CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'system' CHECK (theme IN ('light', 'dark', 'system')),
    default_language VARCHAR(10) DEFAULT 'auto',
    default_model VARCHAR(100) DEFAULT 'ollama:llama3.1',
    voice_input_enabled BOOLEAN DEFAULT FALSE,
    voice_output_enabled BOOLEAN DEFAULT FALSE,
    auto_send_voice BOOLEAN DEFAULT FALSE,
    web_search_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teams & Memberships
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE team_memberships (
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'editor', 'viewer')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- Analytics (aggregation table)
CREATE TABLE analytics_daily (
    date DATE PRIMARY KEY,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    avg_latency_ms INTEGER DEFAULT 0,
    top_languages JSONB DEFAULT '{}',
    top_models JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_conversations_user ON conversations(user_id, updated_at DESC);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_memory_user ON memory(user_id, fact_type);
CREATE INDEX idx_files_conversation ON files(conversation_id);
```

---

## F. TECHNOLOGY STACK

### F.1 Frontend
| Technology | Purpose | Why |
|---|---|---|
| **Next.js 14** (App Router) | React Framework | SSR, streaming, API routes |
| **TypeScript** | Type Safety | Catches bugs at compile time |
| **Tailwind CSS** | Styling | Utility-first, rapid development |
| **shadcn/ui** | Components | Beautiful, accessible primitives |
| **Framer Motion** | Animations | Smooth transitions, chat bubbles |
| **Zustand** | State Management | Lightweight, no boilerplate |
| **TanStack Query** | Server State | Caching, pagination, real-time |
| **React Query** | Data Fetching | Handles async gracefully |
| **WebSocket API** | Real-time | Streaming chat responses |

### F.2 Backend
| Technology | Purpose |
|---|---|
| **FastAPI** (Python) | Main API Framework | Async, auto-docs, type hints |
| **LangChain / LangGraph** | AI Orchestration | Agent workflows, memory |
| **Uvicorn** | ASGI Server | High performance |
| **Pydantic** | Data Validation | Request/response models |
| **SQLAlchemy 2.0** | ORM | Async database operations |
| **Alembic** | Migrations | Schema versioning |
| **Celery** | Background Tasks | Document processing, emails |
| **Redis** (Upstash) | Cache & Broker | Rate limiting, Celery broker |

### F.3 Database & Storage
| Technology | Purpose |
|---|---|
| **PostgreSQL** | Primary Database | Relational data, complex queries |
| **Pinecone** | Vector DB | Semantic search, memory, RAG |
| **Redis** | Cache + Sessions | Fast key-value, pub/sub |
| **AWS S3 / R2** | File Storage | PDFs, images, audio |
| **SQLite** | Development | Local dev (current) |

### F.4 AI Models & APIs
| Provider | Models | Use Case |
|---|---|---|
| **OpenAI** | GPT-4o, GPT-4, GPT-3.5 | Complex reasoning, coding |
| **Anthropic** | Claude 3.5/3 Opus | Long context, safety |
| **Google** | Gemini 1.5 Pro/Flash | Multimodal, cheap |
| **Meta (Ollama)** | Llama 3.1, Mistral | Free, offline, fast |
| **OpenAI Whisper** | Whisper v3 | Speech-to-text |
| **Coqui/Piper** | Multiple voices | Text-to-speech |
| **Hugging Face** | BLOOM, mT5 | Specific language models |
| **Tavily/Serper** | N/A | Real-time web search |

### F.5 Authentication & Security
| Technology | Purpose |
|---|---|
| **NextAuth.js v5** | OAuth (Google, GitHub) |
| **JWT** | Session tokens |
| **Argon2** | Password hashing |
| **Redis** | Session storage |
| **Helmet** | HTTP security headers |

### F.6 Deployment & DevOps
| Technology | Purpose |
|---|---|
| **Docker** | Containerization |
| **Docker Compose** | Local development |
| **GitHub Actions** | CI/CD |
| **Vercel** | Frontend deployment |
| **Render / Fly.io / AWS** | Backend deployment |
| **Prometheus + Grafana** | Monitoring |
| **Sentry** | Error tracking |

---

## G. IMPLEMENTATION ROADMAP (30 Days)

### Phase 1: Foundation (Days 1–7)
**Theme: Core Architecture & Data Layer**

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Project setup: Next.js 14 + FastAPI + Docker | Scaffolded monorepo |
| 2 | Database design + migrations (Alembic) | All tables created |
| 3 | Authentication (OAuth + JWT) | Login, signup, sessions working |
| 4 | API design + FastAPI routes | OpenAPI docs live |
| 5 | Frontend shell (sidebar, layout) | Responsive shell, dark mode |
| 6 | Basic chat UI (messages, input) | Working chat interface |
| 7 | Integration test end-to-end | Demo of basic chat flow |

### Phase 2: Core AI (Days 8–14)
**Theme: Multi-Model Integration & Memory**

| Day | Task | Deliverable |
|-----|------|-------------|
| 8 | Model router implementation | Routes to correct model |
| 9 | OpenAI + Gemini integration | Cloud models working |
| 10 | Ollama local model support | Offline mode working |
| 11 | Claude + Codex integration | All 5 providers working |
| 12 | Conversation memory (short-term) | Context window management |
| 13 | Vector database setup (Pinecone) | Semantic search working |
| 14 | Memory graph (long-term) | Facts persist across chats |

### Phase 3: Advanced Features (Days 15–21)
**Theme: Voice, Documents, Web, Agents**

| Day | Task | Deliverable |
|-----|------|-------------|
| 15 | Voice input (Whisper) | Microphone input working |
| 16 | Voice output (TTS) | Natural speech output |
| 17 | Document upload + RAG | Chat with PDF feature |
| 18 | Web search + citations | Perplexity-style search |
| 19 | Code execution environment | Run code in sandbox |
| 20 | AI Agent workflows | Multi-step task automation |
| 21 | Image understanding (GPT-4V) | Upload image + query |

### Phase 4: Collaboration & Enterprise (Days 22–26)
**Theme: Teams, Sharing, Analytics**

| Day | Task | Deliverable |
|-----|------|-------------|
| 22 | Team workspaces | Create/join teams |
| 23 | Role-based access control | Admin/Editor/Viewer |
| 24 | Chat sharing (public links) | Shareable conversations |
| 25 | Analytics dashboard | Usage, cost, engagement |
| 26 | API key generation | Programmatic access |

### Phase 5: Polish & Launch (Days 27–30)
**Theme: Performance, Testing, Launch**

| Day | Task | Deliverable |
|-----|------|-------------|
| 27 | Performance optimization | < 300ms to first token |
| 28 | Comprehensive testing | Unit, integration, e2e tests |
| 29 | Documentation + Video demo | README, docs, demo video |
| 30 | Production deployment | Live on custom domain |

---

## H. RESUME & PLACEMENT IMPACT

### Why This Project Wins Awards

**1. Technical Depth**
- Demonstrates **full-stack architecture** (Next.js, FastAPI, PostgreSQL, Redis, Pinecone)
- Shows **AI/ML engineering** (LangChain, model routing, RAG, vector search)
- Includes **DevOps** (Docker, CI/CD, monitoring, cloud deployment)
- **Scalability**: Designed for 10K+ concurrent users

**2. Innovation**
- **First student project** with true adaptive model routing
- **Context-aware multilingualism** (not just translation)
- **Production-grade** features: voice, documents, web search, agents
- **Real-world impact**: Solves a genuine problem for 5+ billion non-English speakers

**3. Business Acumen**
- Designed as a **SaaS product** (tiers, teams, analytics)
- **Monetization path**: Free → Pro ($10/mo) → Enterprise ($50/user/mo)
- **Competitive moat**: No other student project combines this breadth

### Resume Bullet Points

**For Software Engineering Roles:**
- *"Architected and built a production-grade AI assistant handling 10K+ users, integrating 5 LLM providers with intelligent routing, achieving <300ms response latency"*
- *"Designed fault-tolerant microservices architecture with FastAPI, PostgreSQL, Redis, and Pinecone, processing 1M+ tokens daily"*

**For AI/ML Engineering Roles:**
- *"Implemented multi-model orchestration using LangGraph, achieving 40% cost reduction through adaptive routing to local/cheap/expensive models"*
- *"Built a RAG system with vector search and web scraping, enabling document chat and real-time research synthesis"*

**For Product/Startup Roles:**
- *"Led end-to-end development of an AI SaaS platform from concept to production, acquiring 500+ beta users and achieving 95% retention"*
- *"Designed subscription tiers and team collaboration features, demonstrating product-market fit"*

### Judging Criteria Alignment

| Criterion | How Aikya Excels |
|---|---|
| **Innovation** | First student project with adaptive model routing, cultural AI, and memory graphs |
| **Technical Complexity** | Multi-modal, multi-lingual, real-time streaming, vector search |
| **Real-World Impact** | Addresses language inequality for 5B non-English speakers |
| **Scalability** | Production architecture, Docker, CI/CD, monitoring |
| **Presentation** | Polished UI (ChatGPT-level), video demo, live deployment |
| **Completeness** | End-to-end platform: auth, payments, teams, API, analytics |

### Awards This Project Is Built To Win

- 🥇 **Smart India Hackathon (SIH) Grand Finale**
- 🏆 **Best Final Year Project (University/State/National)**
- 🚀 **Google Solution Challenge**
- 💡 **Microsoft Imagine Cup**
- 🌟 **Red Bull Basement**
- 🔬 **MIT Solve / Innovate for India**

---

## I. CONCLUSION

**Aikya (ऐक्य)** transforms a simple "language-agnostic chatbot" into a production-grade AI platform that challenges industry incumbents. It combines the **technical depth** of a senior engineering project, the **business acumen** of a startup, and the **social impact** of solving real-world language inequality.

**This is not just a final year project.**
**This is a launchpad for a career in AI.**

*Built with ❤️ in India for the World.*
