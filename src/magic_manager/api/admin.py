"""Admin API (hosted only; admins only): users, invites, sign-outs, per-user flags.

Thin adapter over :mod:`magic_manager.auth.admin`. Nothing here reads a collection
(§25.0: admins manage access and flags, never anyone's cards).
"""
from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel, ConfigDict, Field

from .. import owner_machine
from ..auth import admin


class FlagStateOut(BaseModel):
    name: str
    about: str
    default: bool = Field(description="The server's value (config files + MM_FEATURES).")
    override: bool | None = Field(description="This user's override; null = the default.")
    effective: bool
    owner_paths: list[str] = Field(description="Owner-machine paths in this flag's surface: admins only, whatever the flag says.")


class AdminUserOut(BaseModel):
    id: str
    display_name: str
    email: str | None
    providers: list[str]
    is_admin: bool
    created_at: str
    last_seen_at: str | None
    disabled_at: str | None
    sessions: int = Field(description="Live sessions (signed-in browsers).")
    flags: list[FlagStateOut]


class OwnerPathOut(BaseModel):
    key: str
    feature: str | None
    title: str


class AdminUsersOut(BaseModel):
    users: list[AdminUserOut]
    owner_paths: list[OwnerPathOut]


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    admin: bool = False
    expires_days: int = Field(7, ge=1, le=30)


class InviteOut(BaseModel):
    code: str = Field(description="Shown ONCE — only its hash is stored.")
    url: str | None
    admin: bool
    expires_at: str


class FlagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: bool | None = Field(description="true / false, or null for the default.")


class SignOutOut(BaseModel):
    ended: int


def _user(r: admin.UserRow) -> AdminUserOut:
    return AdminUserOut(**{**r.__dict__, "flags": [FlagStateOut(**f.__dict__) for f in r.flags]})


def users() -> AdminUsersOut:
    return AdminUsersOut(users=[_user(r) for r in admin.users()],
                         owner_paths=[OwnerPathOut(key=p.key, feature=p.feature, title=p.title)
                                      for p in owner_machine.PATHS.values()])


def invite(req: InviteIn, actor: str) -> InviteOut:
    inv = admin.mint_invite(is_admin=req.admin, expires_in=timedelta(days=req.expires_days), created_by=actor)
    return InviteOut(code=inv.code, url=inv.url, admin=inv.is_admin, expires_at=inv.expires_at)


def sign_out(user_id: str) -> SignOutOut:
    return SignOutOut(ended=admin.sign_out(user_id))


def disable(user_id: str, actor: str) -> AdminUserOut:
    admin.disable(user_id, actor=actor)
    return _user(admin.user(user_id))


def enable(user_id: str) -> AdminUserOut:
    admin.enable(user_id)
    return _user(admin.user(user_id))


def set_flag(user_id: str, flag: str, req: FlagIn, actor: str) -> AdminUserOut:
    admin.set_flag(user_id, flag, req.value, actor=actor)
    return _user(admin.user(user_id))
