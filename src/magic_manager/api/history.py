"""Purchase-history surface of the typed API: the acquisition timeline.

Adapts :func:`magic_manager.provenance.history` / ``history_event`` — one entry
per ledger ingest event (what came in, what it still accounts for, its value at
today's local prices), and one entry's exact printings for the drill-in.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards, provenance
from .ingest import PrintingOut

HistoryKind = provenance.HistoryKind


class HistoryEntryOut(BaseModel):
    ingest_id: int
    at: str = Field(description="ISO timestamp of the ingest.")
    method: str
    kind: HistoryKind = Field(description="deck = playable product; pool = card pool (land pack, scene box, Secret Lair…); "
                                          "singles = cards added individually; checklist = a bulk checklist ingest (source product not recorded); "
                                          "unknown = reconstructed bucket with no known source; move = cards pledged to / released from a deck.")
    title: str
    detail: str | None = None
    dated: Literal["acquired", "identified", "reconstructed"] = Field(
        description="acquired = when you added it; identified = when Find products attributed loose cards to it; reconstructed = the V19 backfill.")
    ledgered: bool = Field(description="False for ingests before the ledger existed: their copies are counted in 'Checklists before the ledger' / the unknown buckets.")
    copies_in: int
    copies_out: int = Field(description="Copies later removed or re-attributed to an identified product.")
    held: int = Field(description="Copies this entry still accounts for.")
    printings: int
    value_usd: float = Field(description="Held copies at today's prices.")
    lines: int = Field(description="Rows the ingest touched (checklist rows, deck-move lines).")
    product: str | None = Field(None, description="MTGJSON fileName for product entries.")
    set_code: str | None = None
    deck_slug: str | None = Field(None, description="Deck to open: the moved deck, or the playable product's deck row.")


class HistoryOut(BaseModel):
    entries: list[HistoryEntryOut]
    prices_as_of: str | None = Field(description="Newest local price fetch date (YYYY-MM-DD).")
    stale_sets: list[str] = Field(description="Set codes whose local prices are older than a week (not refreshed).")


class HistoryLineOut(BaseModel):
    printing: PrintingOut
    finish: Literal["nonfoil", "foil"]
    copies_in: int
    copies_out: int
    held: int
    unit_usd: float | None


class HistoryEventOut(BaseModel):
    entry: HistoryEntryOut
    lines: list[HistoryLineOut]


def _entry(h: provenance.HistoryEntry) -> HistoryEntryOut:
    return HistoryEntryOut(**vars(h))


def history() -> HistoryOut:
    h = provenance.history()
    return HistoryOut(entries=[_entry(e) for e in h.entries], prices_as_of=h.prices_as_of, stale_sets=h.stale_sets)


def event(ingest_id: int) -> HistoryEventOut:
    entry, lines = provenance.history_event(ingest_id)
    printings = addcards.printings_for_ids(ln.scryfall_id for ln in lines)
    return HistoryEventOut(entry=_entry(entry), lines=[
        HistoryLineOut(printing=PrintingOut(**printings[ln.scryfall_id]), finish=ln.finish, copies_in=ln.copies_in,
                       copies_out=ln.copies_out, held=ln.held, unit_usd=ln.unit_usd)
        for ln in lines if ln.scryfall_id in printings
    ])
