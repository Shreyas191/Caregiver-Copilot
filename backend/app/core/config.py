"""Application settings loaded from environment variables via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Caregiver Co-Pilot backend.

    All values are loaded from environment variables or a .env file.
    Optional fields default to None until their corresponding features are implemented.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    database_url: str | None = None
    direct_database_url: str | None = None

    # --- Auth (Clerk) ---
    clerk_secret_key: str | None = None
    clerk_jwt_issuer: str | None = None

    # --- Vector DB ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # --- LLM ---
    ollama_base_url: str = "http://localhost:11434"  # kept for legacy scripts

    # --- Per-role model config ---
    # Each role has: BASE_URL (OpenAI-compatible endpoint), API_KEY, MODEL_NAME

    # Router: fast intent classifier — local Ollama
    router_base_url: str = "http://localhost:11434/v1"
    router_api_key: str = "ollama"
    router_model_name: str = "qwen2.5:7b"

    # Generator: agentic tool-use model — GLM-4.5-Air via OpenRouter free tier
    generator_base_url: str = "https://openrouter.ai/api/v1"
    generator_api_key: str = ""
    generator_model_name: str = "z-ai/glm-4.5-air:free"

    # Verifier: structured judgment — Llama-3.3-70B via OpenRouter free tier
    verifier_base_url: str = "https://openrouter.ai/api/v1"
    verifier_api_key: str = ""
    verifier_model_name: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Embeddings: BGE-M3 dense vectors — local Ollama
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_api_key: str = "ollama"
    embedding_model_name: str = "bge-m3:latest"

    # --- External APIs ---
    rxnav_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    openfda_base_url: str = "https://api.fda.gov"

    # --- Google Calendar ---
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # --- Anthropic (CC-047 model comparison) ---
    anthropic_api_key: str | None = None

    # --- Observability ---
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3001"

    # --- Storage ---
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "documents"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
