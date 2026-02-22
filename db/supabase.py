from supabase import create_client, Client

from utils.config import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    """Get Supabase client singleton. Uses secret key for backend (bypasses RLS)."""
    global _client
    if _client is None:
        settings = get_settings()
        key = settings.supabase_service_role_key or settings.supabase_secret_key
        if not settings.supabase_url or not key:
            raise ValueError(
                "Supabase not configured. Set SUPABASE_URL and either "
                "SUPABASE_SECRET_KEY (new) or SUPABASE_SERVICE_ROLE_KEY (legacy) in .env"
            )
        _client = create_client(settings.supabase_url, key)
    return _client
