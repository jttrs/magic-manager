"""Collection surface of the typed API: whole set families with ownership.

Adapts :mod:`magic_manager.collection_view` (the engine) — every computation
lives there. ``families()`` powers the picker; ``family_view()`` returns every
catalogued printing of the requested families with owned/pledged counts and the
classification flags the UI layers on (bulk / chase / standard frame).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import card_earmarks, collection_view, family_status, gallery, scenes, scryfall, scryfall_tags, sets
from .edhrec import FunctionRootOut, function_roots
from .ids import SetCode
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register

BuyTarget = Literal["manapool", "tcgplayer", "cardkingdom", "moxfield", "plain"]


class FamilyOption(BaseModel):
    code: str
    name: str
    owned: bool = Field(True, description="False for a paper family you own nothing from (only listed with include=unowned).")
    year: str | None = Field(None, description="Release year of the family's anchor set (YYYY), when known.")


class SetRefOut(BaseModel):
    code: str
    name: str


class FamilySummaryOut(BaseModel):
    code: str
    name: str
    printings: int
    owned_printings: int
    owned_copies: int
    owned_usd: float
    missing_printings: int
    missing_usd: float
    sets: list[SetRefOut] = Field(default_factory=list, description="Member sets with printings, oldest first.")
    family_released_at: str | None = Field(None, description="The family's release date: its anchor set's (YYYY-MM-DD).")
    catalog_read: bool = Field(True, description="False when the family has no local printings yet (every set unsynced) — read it first.")


class CollectionCardOut(BaseModel):
    scryfall_id: str
    oracle_id: str | None
    name: str
    family: str
    set_code: str
    collector_number: str
    rarity: str
    type_line: str | None
    cmc: float | None
    color_identity: list[str]
    released_at: str | None
    finishes: list[str]
    owned: dict[str, int] = Field(description="finish -> owned copies")
    pledged: dict[str, int] = Field(description="finish -> copies pledged to built decks")
    price_usd: float | None
    price_usd_foil: float | None
    image_uri: str | None
    scryfall_url: str | None
    treatment: str = Field(description="Treatment codes (b, fa, shw, ext, sm, ff; '|'-joined); '' = plain")
    standard_frame: bool
    is_bulk: bool
    is_chase: bool
    functions: list[str] = Field(default_factory=list,
                                 description="Function root keys (Scryfall Tagger roll-up).")
    card_owned: int = Field(0, description="Copies of this card owned in any printing, any set.")
    scene: str | None = Field(None, description="Key of the scene/poster this printing belongs to (see CollectionOut.scenes).")
    earmarked: bool = Field(False, description="The card (any printing) is earmarked.")


class SceneFinishOut(BaseModel):
    finish: Literal["nonfoil", "foil"]
    printings: int = Field(description="Scene printings that exist in this finish.")
    owned: int = Field(description="Of those, printings held in this finish.")
    missing_usd: float = Field(description="Cost to finish the scene in this finish (local prices).")
    unpriced: int = Field(description="Missing printings with no price in this finish.")
    missing_ids: list[str] = Field(description="Missing printings in this finish, collector-number order.")


class SceneOut(BaseModel):
    key: str
    family: str
    rank: int = Field(description="Config order within the family.")
    name: str
    artist: str | None
    kind: Literal["scene", "poster"]
    set_code: str
    cn_lo: int
    cn_hi: int
    printings: int
    owned_printings: int = Field(description="Printings held in any finish.")
    finishes: list[SceneFinishOut]


class CollectionOut(BaseModel):
    families: list[FamilySummaryOut]
    cards: list[CollectionCardOut]
    skipped: list[str] = Field(default_factory=list, description="Codes that didn't resolve to a family.")
    functions: list[FunctionRootOut] = Field(default_factory=list,
                                             description="Function roots, display order.")
    scenes: list[SceneOut] = Field(default_factory=list,
                                   description="Configured scenes/posters of these families, family then config order, with per-finish completion.")


class BuyItem(BaseModel):
    scryfall_id: str
    finish: Literal["nonfoil", "foil"]
    qty: int = Field(1, ge=1)


class BuyListIn(BaseModel):
    target: BuyTarget
    items: list[BuyItem]


class BuyListOut(BaseModel):
    text: str
    lines: int


class CountIn(BaseModel):
    scryfall_id: str
    finish: Literal["nonfoil", "foil"]
    qty: int = Field(ge=0, le=9999)
    expected: int | None = Field(None, ge=0, description="Count the editor started from; refused (409) if the collection moved since.")


class ChecklistIn(BaseModel):
    family: str = Field(min_length=1, description="Family label for the ingest event, e.g. 'Final Fantasy'.")
    changes: list[CountIn] = Field(min_length=1, max_length=5000)


class CountRowOut(BaseModel):
    scryfall_id: str
    finish: str
    old_qty: int
    new_qty: int


class ChecklistOut(BaseModel):
    ingest_id: int | None = Field(description="The checklist ingest event; null when nothing changed.")
    added: int
    updated: int
    zeroed: int
    copies_added: int
    copies_removed: int
    rows: list[CountRowOut]


def families(include_unowned: bool = False) -> list[FamilyOption]:
    """Families the collection touches (owned or registered), for the picker.
    ``include_unowned`` appends every other top-level paper family (newest first)."""
    parents = family_status._owned_family_parents()
    paper = sets.paper_families()
    year = {p["value"]: p["year"] for p in paper}
    out = sorted(
        (FamilyOption(code=c, name=n, year=year.get(c)) for c, n in parents.items()
         if c not in family_status.NON_FAMILY_SETS),
        key=lambda f: f.name,
    )
    if include_unowned:
        out += [FamilyOption(code=p["value"], name=p["label"], owned=False, year=p["year"])
                for p in family_status.unowned_paper_families(set(parents))]
    return out


def _catalog_read(anchor: str) -> bool:
    """Whether a family's catalog is read. The anchor set decides: an owned family's member
    sets (tokens, art cards) are often unsynced. When Scryfall's set list can't be read
    (offline), call it read: the sheet shows what is local and starts no read job."""
    try:
        return not sets.unread_set_codes([anchor])
    except scryfall.ScryfallError:
        return True


def family_view(codes: list[str]) -> CollectionOut:
    summaries: list[FamilySummaryOut] = []
    cards: list[CollectionCardOut] = []
    skipped: list[str] = []
    scene_out: list[SceneOut] = []
    seen: set[str] = set()
    for code in codes:
        try:
            fc, progress = scenes.family_scenes(code)
        except LookupError:
            skipped.append(code)
            continue
        if fc.summary.code in seen:   # two member codes of one family
            continue
        seen.add(fc.summary.code)
        summaries.append(FamilySummaryOut(
            **vars(fc.summary),
            catalog_read=_catalog_read(fc.summary.code),
        ))
        scene_of = scenes.scene_card_keys(fc)
        cards.extend(
            CollectionCardOut(
                **{k: v for k, v in vars(c).items() if k not in ("scryfall_uri", "is_token")},
                scryfall_url=gallery.scryfall_card_url(c.set_code, c.collector_number),
                scene=scene_of.get(c.scryfall_id),
            )
            for c in fc.cards
        )
        scene_out.extend(
            SceneOut(
                **{k: v for k, v in vars(sp).items() if k not in ("card_ids", "finishes")},
                printings=sp.printings,
                finishes=[SceneFinishOut(**vars(sf)) for sf in sp.finishes.values() if sf.printings],
            )
            for sp in progress if sp.printings
        )
    # Tagger function roots for every card in ONE batched lookup (oracle grain).
    summ = scryfall_tags.card_summaries({c.oracle_id for c in cards if c.oracle_id})
    for c in cards:
        s = summ.get(c.oracle_id or "")
        if s:
            c.functions = list(s.functions)
    marked = card_earmarks.marks(c.oracle_id for c in cards)
    for c in cards:
        c.earmarked = c.oracle_id in marked
    return CollectionOut(families=summaries, cards=cards, skipped=skipped,
                         functions=function_roots(), scenes=scene_out)


def buy_list(req: BuyListIn) -> BuyListOut:
    text = collection_view.buy_lines([(i.scryfall_id, i.finish, i.qty) for i in req.items], req.target)
    return BuyListOut(text=text, lines=len([ln for ln in text.splitlines() if ln.strip()]))


def save_checklist(req: ChecklistIn) -> ChecklistOut:
    """Edited checklist counts → ONE ``checklist`` ingest event (modify semantics)."""
    res = sets.apply_counts(
        [sets.CountChange(c.scryfall_id, c.finish, c.qty, c.expected) for c in req.changes],
        label=f"web:checklist · {req.family}",
    )
    return ChecklistOut(**res)


# ---------- job: read a family's catalog ----------

class ReadFamilyInput(BaseModel):
    family: SetCode = Field(description="Any set code of the family to read.")


def _run_read_family(inp: ReadFamilyInput, progress: ProgressFn) -> JobResult:
    _, name, related = family_status.resolve_family(inp.family)
    todo = sets.unread_set_codes([r["code"].lower() for r in related])
    if todo:
        def tick(batch: int, batches: int, cards: int) -> None:
            progress(ProgressEvent(done=batch, total=batches, message=f"{name}: {cards} cards read"))

        sets.sync(todo, progress=tick)
        # What Scryfall holds no (or few) English printings of stays short after a full read:
        # remember it, or the family would read as unread — and be read again — forever.
        sets.mark_read_short(sets.unread_set_codes(todo))
    return JobResult(summary=f"Read {name}" if todo else f"{name} was already read",
                     artifacts=[Artifact(kind="json", label="family",
                                         data={"family": inp.family, "name": name, "synced": todo})])


READ_FAMILY = register(JobSpec(
    name="collection.read_family",
    title="Read a set family",
    description="Fetch a family's printings (Scryfall) for the sets with no local cards, so Collection can show it.",
    input_model=ReadFamilyInput,
    run=_run_read_family,
    scope="shared",
))
