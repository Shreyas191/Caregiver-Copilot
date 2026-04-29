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
    ollama_base_url: str = "http://localhost:11434"

    # --- Model selection ---
    router_model_provider: str = "ollama"
    router_model_name: str = "qwen3:8b"
    generator_model_provider: str = "ollama"
    generator_model_name: str = "glm-4.5-air"
    verifier_model_provider: str = "ollama"
    verifier_model_name: str = "qwen3:30b-a3b"
    embedding_model_provider: str = "ollama"
    embedding_model_name: str = "bge-m3"

    # --- External APIs ---
    rxnav_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    openfda_base_url: str = "https://api.fda.gov"

    # --- Google Calendar ---
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

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
