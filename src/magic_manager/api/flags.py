"""Feature-flag picker API: adapters over :mod:`magic_manager.features`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import features


class FlagRowOut(BaseModel):
    name: str
    title: str
    about: str
    kind: str
    default: bool = Field(description="The value from config/features.toml with features.local.toml applied.")
    everyone: bool | None = Field(None, description="The instance-wide value set in the picker; null = not set.")
    pinned_by_env: bool = Field(description="MM_FEATURES pins this flag, so 'everyone' cannot change what runs.")
    mine: bool | None = Field(None, description="Your own override (hosted only); null = none.")
    effective: bool
    source: Literal["default", "local_file", "everyone", "env", "user"]
    changed_at: str | None = None
    changed_by: str | None = None


class FlagsOut(BaseModel):
    flags: list[FlagRowOut]
    per_user: bool = Field(description="Just-me overrides exist (hosted mode).")


class FlagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["everyone", "me"]
    value: bool | None = Field(description="true / false, or null to clear the value at that scope.")


def _hosted() -> bool:
    return features._hosted()


def _rows(user_id: str | None) -> list[FlagRowOut]:
    from ..auth import store
    defs = features.declared()
    base = features.file_flags()
    resolved = features.resolve(user_id)
    changes = store.last_changes() if store.path().exists() else {}
    names: dict[str, str] = {}

    def who(raw: str | None) -> str | None:
        if raw is None:
            return None
        if raw not in names:
            u = store.get_user(raw)
            names[raw] = u.display_name if u else raw
        return names[raw]

    out = []
    for name, d in defs.items():
        r = resolved[name]
        key = (name, user_id if r.source == "user" else None)
        at, by = changes.get(key, (None, None))
        out.append(FlagRowOut(name=name, title=d.title, about=d.about, kind=d.kind, default=base[name],
                              everyone=r.everyone, pinned_by_env=r.pinned_by_env, mine=r.mine, effective=r.value,
                              source=r.source, changed_at=at, changed_by=who(by)))
    return out


def listing(user_id: str | None) -> FlagsOut:
    return FlagsOut(flags=_rows(user_id), per_user=_hosted())


def set_flag(flag: str, body: FlagIn, user_id: str | None) -> FlagRowOut:
    if flag not in features.declared():
        raise ValueError(f"unknown flag {flag!r} (declared in config/features.toml: {', '.join(features.declared())})")
    if body.scope == "me":
        if not _hosted() or not user_id:
            raise ValueError("just-me overrides need sign-in (hosted mode); set it for everyone instead")
        from ..auth import store
        store.set_override(user_id, flag, body.value, set_by=user_id)
    else:
        features.set_instance(flag, body.value, actor=user_id)
    return next(r for r in _rows(user_id) if r.name == flag)
