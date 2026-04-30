# Setup Guide

## Supabase Database Setup & Migrations

### Creating the Project
1. Go to [Supabase](https://supabase.com/dashboard) and create a new project.
2. Ensure you save the database password you set during creation.
3. Once provisioned, find your Project URL, Anon Key, Service Role Key (under Settings -> API) and your Connection Strings (under Settings -> Database).

### Migration Workflow
Migrations in this project are tracked manually as numbered SQL files under `backend/migrations/` (e.g. `001_extensions.sql`, `002_enums.sql`). We do not use the Supabase migrations CLI to manage schemas to maintain explicit control over what is applied.

**To create a migration:**
1. Create a new `.sql` file in `backend/migrations/` numbered sequentially.
2. Add your `CREATE` or `ALTER` statements.
3. At the bottom of the file, include a `-- down:` section as a comment detailing how to rollback the migration if necessary.

**To apply a migration:**
Run the SQL file against your database using `psql`. Example:
```bash
psql "$DIRECT_DATABASE_URL" -f backend/migrations/001_extensions.sql
```

**To rollback a migration:**
Manually execute the `DROP` or rollback statements noted in the `-- down:` section of the migration file. Never edit a migration file after it has been applied to a shared/production database.

---

## Qdrant (Vector Database) Setup

We use Qdrant for storing and searching vector embeddings.

**To start Qdrant:**
Run the Docker Compose service from the monorepo root:
```bash
docker compose up -d qdrant
```
This will start Qdrant on ports `6333` (HTTP) and `6334` (gRPC).

**To verify it is running:**
1. Open the dashboard at [http://localhost:6333/dashboard](http://localhost:6333/dashboard).
2. Or run the check script: `python backend/scripts/check_qdrant.py`

**To stop Qdrant:**
```bash
docker compose stop qdrant
```

**To reset Qdrant completely (wipes all data):**
```bash
docker compose down -v
```
Or manually delete the `.docker-data/qdrant` directory.

---

## LLM Setup: Ollama (local) + OpenRouter (cloud free tier)

The system uses a transport-agnostic `OpenAICompatibleProvider` for all model roles.
Each role has its own `BASE_URL`, `API_KEY`, and `MODEL_NAME` in `.env`.

### Role assignments

| Role | Model | Provider | Notes |
|---|---|---|---|
| Router | `qwen2.5:7b` | Local Ollama | Fast intent classification |
| Generator | `z-ai/glm-4.5-air:free` | OpenRouter | Agentic tool-use; GLM native tool-calling |
| Verifier | `meta-llama/llama-3.3-70b-instruct:free` | OpenRouter | Strong structured judgment |
| Embeddings | `bge-m3:latest` | Local Ollama | 1024-dim dense vectors |

### Why not run all models locally?

- **GLM-4.5-Air on Ollama (`glm4:latest`) does not support tool calling** via the OpenAI-compatible
  endpoint (returns 400). OpenRouter serves the model with correct native tool-call handling.
- **Running a 70B verifier locally** requires ~40 GB VRAM, not available on most dev machines.
  Llama-3.3-70B via OpenRouter is free, fast, and stronger for judgment tasks.

### Local Ollama setup

Install Ollama and pull only the two local models:

```bash
brew install ollama
brew services start ollama

ollama pull qwen2.5:7b    # router
ollama pull bge-m3:latest # embeddings
```

You do **not** need to pull glm4 or qwen2.5:32b.

### OpenRouter setup

1. Sign up at https://openrouter.ai (free, no credit card required).
2. Create an API key.
3. Add to `.env`:

```env
GENERATOR_API_KEY=sk-or-...
VERIFIER_API_KEY=sk-or-...   # can be the same key
```

**OpenRouter free-tier limits (approximate):**
- ~20 requests/minute
- ~200 messages/day (varies by model and account age)
- No cost for `:free` model variants

The backend implements automatic retry on 429 (rate limit) with a 2-second delay.
If you hit daily limits during development, wait until the next UTC day or upgrade your account.
