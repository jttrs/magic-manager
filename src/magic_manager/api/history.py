"""Purchase-history surface of the typed API: the acquisition timeline.

Adapts :func:`magic_manager.provenance.history` / ``history_event`` — one entry
per ledger ingest event (what came in, what it still accounts for, its value at
today's local prices), and one entry's exact printings for the drill-in.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards, ingest, provenance
from .ingest import PrintingOut

HistoryKind = provenance.HistoryKind


class HistoryEntryOut(BaseModel):
    ingest_id: int
    at: str = Field(description="ISO timestamp of the ingest.")
    method: str
    kind: HistoryKind = Field(description="deck = playable product; pool = card pool (land pack, scene box, Secret Lair…); "
                                          "singles = cards added individually; checklist = a bulk checklist ingest (source product not recorded); "
                                          "unknown = reconstructed bucket with no known source; move = cards pledged to / released from a deck; "
                                          "purchase = a store order read with the browser companion; revert = undid an earlier import.")
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
    purchase_id: int | None = Field(None, description="Purchase entries: the stored store order.")
    paid_usd: float | None = Field(None, description="Purchase entries: what you paid for the copies it still holds (item prices).")
    revertible: bool = Field(False, description="This kind of import can be reverted and hasn't been (the copies may still block it — see the revert plan).")
    reverted_by: int | None = Field(None, description="The revert entry that undid this one.")
    reverts: int | None = Field(None, description="Revert entries: the entry they undid.")


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


# ---------- revert one import (V35) ----------

RevertReason = Literal["not_revertible", "already_reverted", "deck_in_use", "nothing_to_revert", "lines_blocked"]


class RevertLineOut(BaseModel):
    printing: PrintingOut
    finish: Literal["nonfoil", "foil"]
    remove: int = Field(description="Copies the revert removes (the import added them).")
    restore: int = Field(description="Copies the revert puts back (the import removed them).")
    held: int = Field(description="Copies of this printing-finish the import still accounts for.")
    owned: int
    pledged: int = Field(description="Copies pledged to built decks.")
    blocker: Literal["removed", "pledged"] | None = Field(
        None, description="removed = not all of them are still from this import; pledged = in a built deck.")
    pledged_to: list[str] = Field(default_factory=list, description="Built decks holding them (pledged lines).")


class RevertDeckOut(BaseModel):
    slug: str
    name: str
    built: bool
    pledged: int


class RevertPlanOut(BaseModel):
    ingest_id: int
    ok: bool = Field(description="True when the revert can be applied as planned.")
    reason: RevertReason | None = None
    message: str | None = Field(None, description="Why it can't be reverted, in plain words, with the way out.")
    copies_removed: int
    copies_restored: int
    lines: list[RevertLineOut]
    decks: list[RevertDeckOut] = Field(description="Decklists this import saved; deleted with the revert.")
    reverted_by: int | None = None


class RevertOut(BaseModel):
    revert_ingest_id: int
    summary: str
    plan: RevertPlanOut


def plan_out(plan) -> RevertPlanOut:
    printings = addcards.printings_for_ids(ln.scryfall_id for ln in plan.lines)
    lines = [
        RevertLineOut(printing=PrintingOut(**printings[ln.scryfall_id]), finish=ln.finish, remove=ln.remove,
                      restore=ln.restore, held=ln.held, owned=ln.owned, pledged=ln.pledged,
                      blocker=ln.blocker, pledged_to=ln.pledged_to)
        for ln in plan.lines if ln.scryfall_id in printings
    ]
    lines.sort(key=lambda ln: (ln.blocker is None, ln.printing.name, ln.finish))
    return RevertPlanOut(
        ingest_id=plan.ingest_id, ok=plan.ok, reason=plan.refusal_code, message=plan.refusal,
        copies_removed=plan.copies_removed, copies_restored=plan.copies_restored, lines=lines,
        decks=[RevertDeckOut(**vars(d)) for d in plan.decks], reverted_by=plan.reverted_by,
    )


def revert_plan(ingest_id: int) -> RevertPlanOut:
    return plan_out(ingest.revert_event(ingest_id, dry_run=True))


def _n(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def revert(ingest_id: int) -> RevertOut:
    """Apply; raises ``ingest.RevertRefused`` (→ 409 with the plan) when not clean."""
    plan = ingest.revert_event(ingest_id, dry_run=False)
    parts = []
    if plan.copies_removed:
        parts.append(f"removed {_n(plan.copies_removed, 'copy', 'copies')}")
    if plan.copies_restored:
        parts.append(f"put back {_n(plan.copies_restored, 'copy', 'copies')}")
    if plan.decks:
        parts.append(f"deleted {_n(len(plan.decks), 'decklist', 'decklists')}")
    return RevertOut(revert_ingest_id=plan.revert_ingest_id, summary="Reverted: " + ", ".join(parts), plan=plan_out(plan))
