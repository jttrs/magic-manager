"""Auth API models (hosted mode only — local mode has no login)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import auth
from ..auth import store


class UserOut(BaseModel):
    id: str
    display_name: str
    email: str | None
    is_admin: bool


class ProviderOut(BaseModel):
    name: str
    title: str
    login_url: str = Field(description="Start sign-in here (append ?invite=<code> for a first sign-in).")


class MeOut(BaseModel):
    user: UserOut | None = Field(description="Who is signed in; null when nobody is.")
    csrf_token: str | None = Field(description="Send as X-CSRF-Token on every write while signed in.")
    providers: list[ProviderOut]
    profiles_open: bool = Field(description="False while profiles are closed (the kill switch): only admins can sign in.")


def providers() -> list[ProviderOut]:
    return [ProviderOut(name=p, title=auth.PROVIDER_TITLES[p], login_url=f"/api/auth/login/{p}")
            for p in auth.configured_providers()]


def me(session: store.Session | None) -> MeOut:
    user = None
    if session is not None:
        u = session.user
        user = UserOut(id=u.id, display_name=u.display_name, email=u.email, is_admin=u.is_admin)
    return MeOut(user=user, csrf_token=session.csrf_token if session else None,
                 providers=providers(), profiles_open=auth.PROFILES_OPEN)
