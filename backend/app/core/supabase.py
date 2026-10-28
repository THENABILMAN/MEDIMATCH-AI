from functools import lru_cache
from typing import Optional
from supabase import Client, create_client
from app.core.config import settings


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """Returns a Supabase client configured with the public anon key (respects RLS)."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache()
def get_supabase_admin_client() -> Optional[Client]:
    """Returns a Supabase client configured with the service role key (bypasses RLS).
    
    WARNING: Only use this on the backend for administrative operations,
    user creation, and trusted audit logging. Never expose service role key to clients.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
