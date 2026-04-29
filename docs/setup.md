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

## Ollama (Local LLMs) Setup

We use Ollama to run the required models locally.

**To install Ollama on macOS:**
```bash
brew install ollama
brew services start ollama
```

**Required Models & Substitutions:**
- Embedding Model: `bge-m3`
- Router Chat Model: `qwen2.5:7b` (Substituted for `qwen3:8b` as Qwen3 is not available on Ollama registry yet)
- Generator Chat Model: `glm4` (Substituted for `glm-4.5-air` as exact tag is not available)
- Verifier Chat Model: `qwen2.5:32b` (Substituted for `qwen3:30b-a3b` as exact tag is not available)

**To pull the models:**
```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
ollama pull glm4
ollama pull qwen2.5:32b
```
