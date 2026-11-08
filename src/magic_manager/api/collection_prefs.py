"""'What counts' preferences API: adapters over :mod:`magic_manager.collection_prefs`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .. import collection_prefs


class ChoiceOut(BaseModel):
    value: str
    label: str


class PrefOut(BaseModel):
    key: str
    title: str
    about: str
    kind: Literal["choice", "multi"]
    choices: list[ChoiceOut]
    value: str | list[str]
    default: str | list[str]
    changed: bool


class PrefsOut(BaseModel):
    prefs: list[PrefOut]


class PrefIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | list[str] | None = None  # null resets the preference


def listing() -> PrefsOut:
    return PrefsOut(prefs=[PrefOut(**d) for d in collection_prefs.describe()])


def set_pref(key: str, req: PrefIn) -> PrefsOut:
    """Raises ``ValueError`` (bad value) / ``LookupError`` (unknown key); returns the full listing."""
    collection_prefs.update(key, req.value)
    return listing()
