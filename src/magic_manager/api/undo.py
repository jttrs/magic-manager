"""Undo surface of the typed API: the one restore point (see :mod:`magic_manager.undo`)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import undo


class UndoSummary(BaseModel):
    copies: int
    printings: int
    decks: int
    built: int
    wishlist: int
    earmarks: int


class UndoDetail(BaseModel):
    label: str = Field(description="Plain-words group of your data, e.g. 'deck lists'.")
    rows: int = Field(description="Rows added, removed or edited since the restore point.")


class UndoOut(BaseModel):
    taken_at: str = Field(description="UTC ISO time the restore point was taken.")
    reason: str
    restorable: bool = Field(description="False when the database changed shape since.")
    current: UndoSummary
    snapshot: UndoSummary
    changes: UndoSummary = Field(description="Snapshot minus current: what restoring would change.")
    details: list[UndoDetail] = Field(default_factory=list, description="Every group of your data a restore would roll back, with how many rows differ.")


def info() -> UndoOut | None:
    data = undo.info()
    return UndoOut(**data) if data else None


def restore() -> UndoOut:
    return UndoOut(**undo.restore())
