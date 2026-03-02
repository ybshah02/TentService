"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "TentService"
    debug: bool = False
    # When False, debug API routes (/api/v1/debug/*) are not mounted
    debug_routes_enabled: bool = True

    # Supabase - from Project Settings → API Keys
    # New keys: sb_publishable_... and sb_secret_...
    # Legacy: service_role JWT (if sb_secret_ causes "Invalid API key", use Legacy tab)
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_service_role_key: str = ""  # Legacy JWT - use if sb_secret_ fails
    # JWT secret for verifying access tokens (Project Settings → API → JWT Settings)
    supabase_jwt_secret: str = ""

    # Set to false to bypass auth (e.g. for core app development). All protected routes accept requests without a token.
    auth_enabled: bool = True

    # Database - use Supabase connection string (Project Settings → Database)
    # Format: postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    database_url: str = ""

    # Seed script: use existing auth user as admin (create in Supabase Dashboard first)
    seed_admin_user_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


_settings = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
