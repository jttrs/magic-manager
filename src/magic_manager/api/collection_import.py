"""Collection import: a companion read (internal — ``companion`` flag) or another
app's exported collection file (no flag — :func:`preview_file` / :func:`apply_file`).

The companion reads your Moxfield collection or one binder in your own browser
(``extension/src/readers/moxfield-collection.js``); the app posts only the card
lines here. Two thin adapters over ``collection_sync``: ``preview`` (what would
change — nothing written) and ``apply`` (ONE ``collection-import`` ingest event,
``add`` or ``replace`` chosen per import; printings the read doesn't list are
never touched). Strict inputs: unknown fields are refused, sizes capped.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import collection_sync, features, scraper_health
from .companion import CompanionFailure

_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
MAX_LINES = 60_000


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CollectionLineIn(_Strict):
    """One printing × finish from the read (copies of the same printing summed)."""
    quantity: int = Field(ge=1, le=99_999)
    finish: Literal["nonfoil", "foil", "etched"]
    scryfall_id: str | None = Field(None, pattern=_UUID)
    set: str | None = Field(None, max_length=10, pattern=r"^[0-9A-Za-z]+$")
    # Any collector number Scryfall uses (e.g. SLD "633Φ"), but no spaces or markup.
    cn: str | None = Field(None, max_length=12, pattern=r"^[^\s<>\"'&]+$")
    name: str | None = Field(None, max_length=200)
    proxy: bool = False
    digital: bool = False


class CollectionReadIn(_Strict):
    source: Literal["moxfield"]
    scope: Literal["collection", "binder"]
    id: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{4,64}$", description="The shared link's id; none = your own whole collection.")
    name: str | None = Field(None, max_length=200, description="The binder's name, for the ingest label.")
    lines: list[CollectionLineIn] = Field(max_length=MAX_LINES)


class ImportRowOut(BaseModel):
    scryfall_id: str
    finish: Literal["nonfoil", "foil"]
    name: str | None
    set: str | None
    collector_number: str | None
    current: int = Field(description="Copies you own now.")
    incoming: int = Field(description="Copies in the read.")
    pledged: int = Field(0, description="Copies in built decks — replace can't go below this.")


class NotFoundOut(BaseModel):
    qty: int
    name: str | None
    set: str | None
    collector_number: str | None
    finish: str


class SkippedOut(BaseModel):
    proxy: int = 0
    digital: int = 0


class CollectionPreviewOut(BaseModel):
    label: str
    rows: list[ImportRowOut]
    not_found: list[NotFoundOut]
    skipped: SkippedOut
    not_in_read: int = Field(description="Printings you own that the read doesn't list — always left as they are.")
    already_imported_at: str | None = Field(description="When this exact read was imported before, if it was.")
    warnings: list[str] = []


class CollectionApplyIn(CollectionReadIn):
    mode: Literal["add", "replace"]
    force: bool = Field(False, description="Add an identical read again (it was imported before).")


class CollectionApplyOut(BaseModel):
    mode: Literal["add", "replace"]
    ingest_id: int
    added: int = Field(description="Printings new to your collection.")
    updated: int = Field(description="Printings whose count changed.")
    not_found: int
    label: str


def label_for(req: CollectionReadIn) -> str:
    """The ingest label: the binder name (owner: binders are only a way to pick
    what to import; the name lands in the label, nowhere else)."""
    what = (f"binder · {req.name}" if req.name else "binder") if req.scope == "binder" \
        else ("shared collection" if req.id else "collection")
    return f"web:{req.source} {what}"


def _lines(req: CollectionReadIn) -> list[dict]:
    if not req.lines:
        raise CompanionFailure("collection.empty")
    return [ln.model_dump() for ln in req.lines]


def preview(req: CollectionReadIn) -> CollectionPreviewOut:
    features.require("companion")
    p = collection_sync.preview_lines(_lines(req))
    if not p["rows"]:
        raise CompanionFailure("collection.empty")
    scraper_health.record_use(f"companion-collection/{req.source}", "ok")
    return CollectionPreviewOut(label=label_for(req), **{k: p[k] for k in ("rows", "not_found", "skipped", "not_in_read", "already_imported_at", "warnings")})


def apply(req: CollectionApplyIn) -> CollectionApplyOut:
    features.require("companion")
    label = label_for(req)
    try:
        out = collection_sync.apply_lines(_lines(req), mode=req.mode, label=label, force=req.force)
    except collection_sync.NothingToImport as e:
        raise CompanionFailure("collection.empty") from e
    return CollectionApplyOut(mode=req.mode, ingest_id=out["ingest_id"], added=out["added"], updated=out["updated"],
                              not_found=out["not_found"], label=label)


# ---------- exported collection files (no companion needed) ----------

MAX_FILE_CHARS = 25_000_000


class CollectionFormatOut(BaseModel):
    id: str
    name: str = Field(description="The app, as the user knows it.")
    how: str = Field("", description="Where that app's collection export lives.")


class CollectionFileIn(_Strict):
    """An exported collection file, read in the browser and posted as text."""
    filename: str = Field(max_length=255)
    text: str = Field(max_length=MAX_FILE_CHARS)
    format: str | None = Field(None, max_length=40, pattern=r"^[a-z0-9_-]+$", description="Skip detection: the service id.")


class CollectionFilePreviewOut(CollectionPreviewOut):
    format: str = Field(description="The service id the file was read as.")
    format_name: str


class CollectionFileApplyIn(CollectionFileIn):
    mode: Literal["add", "replace"]
    force: bool = Field(False, description="Add an identical read again (it was imported before).")


def formats() -> list[CollectionFormatOut]:
    return [CollectionFormatOut(**f) for f in collection_sync.importable_formats()]


def _read_file(req: CollectionFileIn) -> collection_sync.ExportRead:
    """Raises ``BadFile`` (unknown format, unreadable, past the caps → 422) and
    ``NothingToImport`` when the file has no card lines."""
    try:
        read = collection_sync.read_export(req.text, service=req.format)
    except LookupError as e:
        raise collection_sync.UnknownFormat(str(e)) from e
    if not read.lines:
        raise collection_sync.NothingToImport("This file has no card lines to import.")
    return read


def file_label(read: collection_sync.ExportRead, filename: str) -> str:
    return f"web:file {read.name} · {filename}"[:300]


def preview_file(req: CollectionFileIn) -> CollectionFilePreviewOut:
    read = _read_file(req)
    p = collection_sync.preview_lines(read.lines)
    if not p["rows"] and not p["not_found"]:
        raise collection_sync.NothingToImport("This file has only proxies or digital copies — nothing to import.")
    return CollectionFilePreviewOut(
        label=file_label(read, req.filename), format=read.service, format_name=read.name,
        **{k: p[k] for k in ("rows", "not_found", "skipped", "not_in_read", "already_imported_at", "warnings")})


def apply_file(req: CollectionFileApplyIn) -> CollectionApplyOut:
    read = _read_file(req)
    label = file_label(read, req.filename)
    out = collection_sync.apply_lines(read.lines, mode=req.mode, label=label, force=req.force)
    return CollectionApplyOut(mode=req.mode, ingest_id=out["ingest_id"], added=out["added"], updated=out["updated"],
                              not_found=out["not_found"], label=label)
