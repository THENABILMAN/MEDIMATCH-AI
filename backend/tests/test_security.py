"""Regression tests: tokens are only trusted when Supabase confirms them."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import deps
from app.core import security
from app.core.config import settings

FORGED_ADMIN_TOKEN = jwt.encode(
    {"sub": "a0000000-0000-0000-0000-000000000001", "user_metadata": {"role": "admin"}},
    "attacker-key",
    algorithm="HS256",
)


@pytest.fixture(params=["development", "production"])
def live_environment(request, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", request.param)
    return request.param


def _supabase_returning(**kwargs) -> MagicMock:
    supabase = MagicMock()
    supabase.auth.get_user = MagicMock(**kwargs)
    return supabase


def test_forged_token_rejected_when_supabase_rejects_it(live_environment, monkeypatch):
    supabase = _supabase_returning(side_effect=ValueError("bad jwt"))
    monkeypatch.setattr(security, "get_supabase_client", lambda: supabase)

    with pytest.raises(HTTPException) as exc:
        security.verify_supabase_token(FORGED_ADMIN_TOKEN)
    assert exc.value.status_code == 401


def test_forged_token_rejected_when_supabase_returns_no_user(live_environment, monkeypatch):
    supabase = _supabase_returning(return_value=SimpleNamespace(user=None))
    monkeypatch.setattr(security, "get_supabase_client", lambda: supabase)

    with pytest.raises(HTTPException) as exc:
        security.verify_supabase_token(FORGED_ADMIN_TOKEN)
    assert exc.value.status_code == 401


def test_token_not_decoded_when_supabase_is_not_configured(live_environment, monkeypatch):
    monkeypatch.setattr(security, "get_supabase_client", lambda: None)

    with pytest.raises(HTTPException) as exc:
        security.verify_supabase_token(FORGED_ADMIN_TOKEN)
    assert exc.value.status_code == 503


def test_confirmed_token_returns_supabase_identity(live_environment, monkeypatch):
    user = SimpleNamespace(id="u1", email="u1@test.com", user_metadata={}, app_metadata={})
    supabase = _supabase_returning(return_value=SimpleNamespace(user=user))
    monkeypatch.setattr(security, "get_supabase_client", lambda: supabase)

    assert security.verify_supabase_token("real-token")["sub"] == "u1"


def test_profile_failure_never_grants_role_from_metadata(live_environment, monkeypatch):
    """user_metadata is editable by the user, so it must not decide the role."""
    monkeypatch.setattr(
        deps,
        "verify_supabase_token",
        lambda _token: {"sub": "u1", "email": None, "user_metadata": {"role": "admin"}},
    )

    def failing_profile(**_kwargs):
        raise RuntimeError("database connection lost")

    monkeypatch.setattr(deps, "get_user_profile", failing_profile)

    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"))
    assert exc.value.status_code == 503
