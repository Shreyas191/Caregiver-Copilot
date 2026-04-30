# 🏥 Caregiver Co-Pilot

An AI-powered assistant for family caregivers managing the health and well-being of their loved ones. Built with a multi-model architecture using local and cloud LLMs, it provides reliable clinical guidance, tracks vitals and episodes, and helps caregivers communicate effectively with healthcare providers.

## ✨ Features

- **Care Recipient Management** — Onboard care recipients with conditions, allergies, medications, and provider contacts
- **Medication Autocomplete** — Search and add standardized medications via the NIH RxNav database (with 24h server-side caching)
- **AI Chat Agent** — ReAct-style agent loop that understands clinical context, logs vitals/episodes, and provides actionable guidance
- **Vital & Episode Tracking** — Automatically records vital signs and health episodes mentioned in conversation
- **Safety-First Design** — Built-in guardrails: no dosing, no diagnosing, no medication changes — always defers to providers
- **Real-time Streaming** — Server-Sent Events (SSE) for word-by-word response streaming

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│          Next.js 14 · Clerk Auth · SSE           │
└────────────────────┬────────────────────────────┘
                     │ REST + SSE
┌────────────────────▼────────────────────────────┐
│                  Backend API                     │
│         FastAPI · SQLAlchemy 2.0 Async           │
├──────────────────────────────────────────────────┤
│              Agent Layer (v0 Loop)               │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Context  │  │   Write   │  │   Clinical   │  │
│  │  Tools   │  │   Tools   │  │    Tools     │  │
│  │(4 tools) │  │ (2 tools) │  │  (planned)   │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
├──────────────────────────────────────────────────┤
│              Model Providers                     │
│  Generator: GLM-4.5-Air (OpenRouter)             │
│  Router: Qwen 2.5 7B (Ollama) — planned         │
│  Verifier: Llama 3.3 70B (OpenRouter) — planned  │
│  Embeddings: BGE-M3 (Ollama) — planned           │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Supabase Postgres                   │
│  caregivers · care_recipients · medications      │
│  vitals · episodes · conversation_threads        │
│  conversation_messages · external_api_cache      │
└──────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, shadcn/ui, Clerk |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 async |
| Database | Supabase (PostgreSQL) |
| LLM (Generator) | GLM-4.5-Air via OpenRouter (free tier) |
| LLM (Local) | Ollama (Qwen 2.5, BGE-M3) |
| External APIs | NIH RxNav (medications) |
| Auth | Clerk (JWT) |

## 📁 Project Structure

```
caregiver-copilot/
├── backend/
│   ├── app/
│   │   ├── agent/           # AI agent loop + tools
│   │   │   ├── prompts/     # System prompts
│   │   │   ├── tools/       # Context (read) + write tools
│   │   │   └── v0_loop.py   # ReAct agent loop
│   │   ├── core/            # Config, database, security
│   │   ├── integrations/    # RxNav API client
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── providers/       # LLM provider abstraction
│   │   ├── routes/          # FastAPI endpoints
│   │   ├── schemas/         # Pydantic request/response
│   │   ├── services/        # Business logic
│   │   └── tests/           # Pytest test suite
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   ├── components/      # UI components
│   │   ├── hooks/           # Custom React hooks
│   │   └── lib/             # API client, SSE utilities
│   └── package.json
└── docs/                    # Setup & API documentation
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Supabase** account (for PostgreSQL)
- **Clerk** account (for authentication)
- **OpenRouter** API key (free tier — for GLM-4.5-Air)
- **Ollama** (optional — for local models)

### 1. Clone & configure

```bash
git clone git@github.com:Shreyas191/Caregiver-AI-Copilot.git
cd Caregiver-AI-Copilot/caregiver-copilot
cp .env.example .env
# Fill in your keys: DATABASE_URL, CLERK_SECRET_KEY, GENERATOR_API_KEY, etc.
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Health check: `GET /health`

### 3. Frontend setup

```bash
cd frontend
cp .env.local.example .env.local
# Fill in NEXT_PUBLIC_API_URL and Clerk keys
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### 4. Run tests

```bash
cd backend
source .venv/bin/activate
pytest app/tests/ -v
```

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Supabase Postgres connection string (asyncpg) |
| `CLERK_SECRET_KEY` | ✅ | Clerk backend secret |
| `CLERK_JWT_ISSUER` | ✅ | Clerk JWT issuer URL |
| `GENERATOR_API_KEY` | ✅ | OpenRouter API key for GLM-4.5-Air |
| `GENERATOR_BASE_URL` | ✅ | `https://openrouter.ai/api/v1` |
| `GENERATOR_MODEL_NAME` | ✅ | `z-ai/glm-4.5-air:free` |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend URL (e.g., `http://localhost:8000`) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | Clerk frontend key |

## 📋 Implemented Tasks

| Task | Description | Status |
|------|-------------|--------|
| CC-001 | Next.js frontend setup | ✅ |
| CC-002 | FastAPI backend foundation | ✅ |
| CC-003 | Supabase schema & migrations | ✅ |
| CC-004 | Clerk authentication integration | ✅ |
| CC-005 | ORM models for all tables | ✅ |
| CC-006 | Care recipient CRUD endpoints | ✅ |
| CC-007 | Care recipient onboarding form | ✅ |
| CC-008–011 | Schema refinements & validation | ✅ |
| CC-012 | Medication autocomplete (RxNav) | ✅ |
| CC-013 | Dashboard & profile pages | ✅ |
| CC-014 | Chat UI with SSE streaming | ✅ |
| CC-015 | Ollama/OpenAI provider abstraction | ✅ |
| CC-016 | Context-reading agent tools | ✅ |
| CC-017 | Write tools (log_vital, log_episode) | ✅ |
| CC-018 | v0 Agent loop (GLM-4.5-Air) | ✅ |

## 📄 License

This project is for educational and research purposes.
