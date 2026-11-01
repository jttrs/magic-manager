"""Account API (§25.1 H10): download your data, delete your account (hosted).

Thin over :mod:`magic_manager.account`; whose data is the bound user (the web gate
binds the signed-in user from the server session — never from client input).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import account


class DeleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: str = Field(max_length=64, description=f"Type “{account.DELETE_CONFIRMATION}” to confirm.")


class DeleteOut(BaseModel):
    deleted: bool
    files_removed: int = Field(description="Collection files removed (the file, its restore point and snapshots).")


def confirmed(text: str) -> bool:
    return " ".join(text.split()).lower() == account.DELETE_CONFIRMATION


def export() -> account.Export:
    return account.export()


def delete(user_id: str) -> DeleteOut:
    out = account.delete_account(user_id)
    return DeleteOut(deleted=True, files_removed=len(out.files))
