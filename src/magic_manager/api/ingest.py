"""Add-cards surface of the typed API: search a printing, paste a list, or bring
a deck/precon, resolve every line to exact printings, then commit to inventory.

Adapts :mod:`magic_manager.addcards` (the engine) — every computation lives
there. Writes go through ONE ingest event per commit (``ingest.open_ingest_event``)
labelled ``web:<source>``, reusing existing methods (``adhoc`` for search adds,
``import-block`` for paste/deck lists, ``precon`` for precon imports), so the
provenance ledger stays exact with no migration.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register

Finish = Literal["nonfoil", "foil"]
PasteFormat = Literal["auto", "moxfield", "tcgplayer", "names"]


class PrintingOut(BaseModel):
    """One exact printing a line can resolve to (what the picker shows)."""
    scryfall_id: str
    oracle_id: str | None
    name: str
    set_code: str
    set_name: str | None
    collector_number: str
    rarity: str
    finishes: list[Finish] = Field(description="Inventory finishes (etched counts as foil).")
    treatment: str = Field(description="treatments.compute_treatment code, '' for a standard frame.")
    image_uri: str | None
    price_usd: float | None
    price_usd_foil: float | None
    released_at: str | None
    type_line: str | None = None
    cmc: float | None = None
    owned: dict[str, int] = Field(default_factory=dict, description="Copies you already own, per finish.")
    free: int = Field(0, description="Owned copies no built deck has pledged (all finishes).")


class SearchOut(BaseModel):
    query: str
    source: Literal["local", "scryfall"]
    printings: list[PrintingOut]


class ResolveIn(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    format: PasteFormat = "auto"


class ResolvedLineOut(BaseModel):
    line: int = Field(description="1-based line number in the pasted text (0 for fetched decks).")
    raw: str
    qty: int
    name: str
    finish: Finish
    section: str
    status: Literal["exact", "ambiguous", "unresolved"]
    candidates: list[PrintingOut] = Field(description="Exact: one. Ambiguous: every printing of the name, best guess first. Unresolved: empty.")
    chosen: str | None = Field(description="scryfall_id of the default pick (None when unresolved).")
    note: str | None = None


class ResolveOut(BaseModel):
    format: Literal["moxfield", "tcgplayer", "names", "deck"]
    lines: list[ResolvedLineOut]
    warnings: list[str] = Field(default_factory=list)
    deck_name: str | None = None


class CommitItem(BaseModel):
    scryfall_id: str
    finish: Finish
    qty: int = Field(ge=1, le=10_000)


class CommitIn(BaseModel):
    items: list[CommitItem] = Field(min_length=1)
    source: Literal["search", "paste", "deck"]
    label: str | None = Field(None, max_length=200, description="Free text recorded on the ingest event (e.g. a deck name).")


class CommitOut(BaseModel):
    ingest_id: int
    copies: int
    printings: int
    summary: str


class PreconOptionOut(BaseModel):
    file_name: str
    name: str
    set_code: str
    type: str
    release_date: str | None
    default_state: Literal["built", "deconstructed"]
    owned_built: int
    owned_deconstructed: int


def search(q: str, limit: int = 60) -> SearchOut:
    return SearchOut(**addcards.search_printings(q, limit=limit))


def resolve(body: ResolveIn) -> ResolveOut:
    return ResolveOut(**addcards.resolve_text(body.text, fmt=body.format))


def commit(body: CommitIn) -> CommitOut:
    return CommitOut(**addcards.commit(
        [(i.scryfall_id, i.finish, i.qty) for i in body.items], source=body.source, label=body.label,
    ))


def precons(q: str = "", limit: int = 50) -> list[PreconOptionOut]:
    return [PreconOptionOut(**p) for p in addcards.precon_catalog(q, limit=limit)]


# ---------- jobs ----------

class AddPreconInput(BaseModel):
    file_name: str = Field(min_length=1, description="MTGJSON deck fileName from the precon catalog.")
    copies: int = Field(1, ge=1, le=50)
    state: Literal["auto", "built", "deconstructed"] = Field(
        "auto", description="auto = mtgjson.default_precon_state (pool-shaped products go loose).",
    )


def _run_add_precon(inp: AddPreconInput, progress: ProgressFn) -> JobResult:
    progress(ProgressEvent(0, None, f"Importing {inp.file_name}…"))
    res = addcards.add_precon(inp.file_name, copies=inp.copies, state=inp.state)
    return JobResult(summary=res["summary"], artifacts=[Artifact(kind="json", label="result", data=res)])


ADD_PRECON = register(JobSpec(
    name="ingest.precon",
    title="Add a precon",
    description="Add every card of a preconstructed product to your collection (and track it as a deck).",
    input_model=AddPreconInput,
    run=_run_add_precon,
    mutates=True,
))


class FetchDeckInput(BaseModel):
    url: str = Field(min_length=8, max_length=500, description="Archidekt, MTGGoldfish, ManaBox, Scryfall or Moxfield deck URL.")


def _run_fetch_deck(inp: FetchDeckInput, progress: ProgressFn) -> JobResult:
    progress(ProgressEvent(0, None, "Fetching deck…"))
    out = addcards.fetch_deck_lines(inp.url, progress=lambda msg: progress(ProgressEvent(0, None, msg)))
    resolved = ResolveOut(**out)
    n = sum(line.qty for line in resolved.lines)
    return JobResult(
        summary=f"{resolved.deck_name or 'Deck'} · {n} cards to review",
        artifacts=[Artifact(kind="json", label="lines", data=resolved.model_dump())],
    )


FETCH_DECK = register(JobSpec(
    name="ingest.fetch_deck",
    title="Fetch a deck list",
    description="Read a deck from a deck-builder URL and resolve it to printings for review (adds nothing yet).",
    input_model=FetchDeckInput,
    run=_run_fetch_deck,
))
