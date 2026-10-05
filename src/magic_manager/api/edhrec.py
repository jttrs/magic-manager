"""EDHREC surface of the typed API: the bulk cache-warm job + compare/search reads.

Thin adapters over :mod:`magic_manager.edhrec` — every computation lives there.
Response models are Pydantic so delivery layers get a typed, schema'd contract
(FastAPI → OpenAPI → generated TS client) without re-describing engine fields.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from pydantic import BaseModel, Field, model_validator

from .. import config, db, edhrec, legality
from .. import gallery
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


# ---------- job: bulk cache-warm ----------

class SyncBulkInput(BaseModel):
    """Warm EDHREC for a card universe: exactly one of ``selector`` or ``families``."""
    selector: str | None = Field(None, description="Selector DSL, e.g. 'set:fin+related' or 'inventory'.")
    families: list[str] = Field(default_factory=list, description="Set-family anchors, e.g. ['fin','msh'].")
    card_type: str | None = Field(None, description="Case-insensitive type_line substring, e.g. 'legendary creature'.")
    resume: bool = Field(True, description="Skip cards whose EDHREC pages are already cached.")

    @model_validator(mode="after")
    def _one_source(self):
        if bool(self.selector) == bool([f for f in self.families if f.strip()]):
            raise ValueError("provide exactly one of selector or families")
        return self


def _run_sync_bulk(inp: SyncBulkInput, progress: ProgressFn) -> JobResult:
    names = edhrec.names_for_bulk(
        selector=inp.selector, families=inp.families, card_type=inp.card_type,
    )
    progress(ProgressEvent(0, len(names), f"{len(names)} cards resolved; checking cache…"))

    def _tick(i: int, total: int, name: str, tag: str) -> None:
        level = "error" if tag.startswith(("ERROR", "BUG")) else "info"
        progress(ProgressEvent(i, total, f"{name} — {tag}", level))

    def _resolving(i: int, total: int, name: str) -> None:
        progress(ProgressEvent(i, total, f"Checking {name}…"))

    res = edhrec.sync_bulk(names, resume=inp.resume, progress=_tick, on_resolve=_resolving)
    summary = (f"{res.total} cards · {res.already} already cached · {res.ok} synced "
               f"({res.eligible} commanders) · {res.failed} failed")
    return JobResult(summary=summary, artifacts=[
        Artifact(kind="json", label="result", data=asdict(res)),
    ])


SYNC_BULK = register(JobSpec(
    name="edhrec.sync_bulk",
    title="Warm EDHREC cache",
    description="Fetch EDHREC commander + card pages for every card in a selector or set family.",
    input_model=SyncBulkInput,
    run=_run_sync_bulk,
))


# ---------- read: commander compare ----------

class OracleTagOut(BaseModel):
    """A Scryfall Tagger oracle tag (``id`` is the stable UUID)."""
    id: str
    slug: str
    label: str


class FunctionRootOut(BaseModel):
    """A curated function root (``config/function_tags.toml``), in display order."""
    key: str
    label: str


class CompareCardOut(BaseModel):
    name: str
    oracle_id: str | None
    slug: str
    bucket: str
    tags: list[str]
    a_pct: float | None
    b_pct: float | None
    a_decks: int | None
    b_decks: int | None
    delta: float | None
    synergy_a: float | None
    synergy_b: float | None
    trend_a: float | None
    trend_b: float | None
    type_line: str | None
    cmc: float | None
    mana_cost: str | None
    color_identity: list[str] | None
    rarity: str | None
    lowest_usd: float | None
    lowest_usd_foil: float | None
    scryfall_id: str | None
    image_uri: str | None
    set_code: str | None
    collector_number: str | None
    scryfall_url: str | None
    functions: list[str] = Field(default_factory=list,
                                 description="Function root keys (Scryfall Tagger roll-up).")
    oracle_tags: list[OracleTagOut] = Field(default_factory=list,
                                            description="Top Tagger oracle tags by weight.")
    owned: int = Field(0, description="Copies you own across every printing.")
    free: int = Field(0, description="Owned copies no built deck has pledged.")


class CompareOut(BaseModel):
    name_a: str
    name_b: str | None = Field(None, description="None when exploring one commander.")
    slug_a: str
    slug_b: str | None = None
    cards: list[CompareCardOut]
    functions: list[FunctionRootOut] = Field(default_factory=list,
                                             description="Function roots, display order.")


def compare(a: str, b: str | None = None) -> CompareOut:
    """One commander's recommended cards (all a_only), or two partitioned
    a_only / both / b_only. Display printing = first standard printing (engine-side);
    owned / free from the collection (oracle grain)."""
    from .. import explore

    res = edhrec.compare_commanders(a, b)
    facts = explore.facts_for([c.oracle_id for c in res.cards if c.oracle_id])
    return CompareOut(
        name_a=res.name_a, name_b=res.name_b, slug_a=res.slug_a, slug_b=res.slug_b,
        cards=[
            CompareCardOut(
                **asdict(c),
                scryfall_url=gallery.scryfall_card_url(c.set_code, c.collector_number),
                owned=(f := facts.get(c.oracle_id or "")) and f.owned or 0,
                free=f and f.free or 0,
            )
            for c in res.cards
        ],
        functions=function_roots(),
    )


def function_roots() -> list[FunctionRootOut]:
    """The configured function roots (key + label) in display order."""
    return [FunctionRootOut(key=r["key"], label=r["label"])
            for r in config.function_tags()["roots"]]


# ---------- read: commander picker ----------

class CommanderOption(BaseModel):
    name: str
    oracle_id: str | None
    type_line: str | None
    color_identity: list[str]
    image_uri: str | None
    cached: bool = Field(description="EDHREC commander page already in the local cache.")


def search_commanders(q: str, *, limit: int = 20) -> list[CommanderOption]:
    """Commander-eligible cards whose name contains ``q`` (local ``cards`` only),
    cached-on-EDHREC first, then prefix matches, then alphabetical. Free-text
    names not in the local DB still work downstream (compare resolves via
    Scryfall) — this only powers suggestions."""
    q = (q or "").strip()
    if not q:
        return []
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT oracle_id, name, type_line, oracle_text, color_identity, image_uri
            FROM cards
            WHERE name LIKE ? COLLATE NOCASE AND is_token = 0
              AND (type_line LIKE '%Legendary%' OR oracle_text LIKE '%can be your commander%'
                   OR type_line LIKE '%Background%')
            GROUP BY oracle_id
            """,
            (f"%{q}%",),
        ).fetchall()
        cached = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT slug FROM edhrec_pages WHERE page_type='commander'"
            )
        }
    out = []
    for r in rows:
        if not legality.is_commander_eligible(dict(r)):
            continue
        ci = r["color_identity"]
        out.append(CommanderOption(
            name=r["name"], oracle_id=r["oracle_id"], type_line=r["type_line"],
            color_identity=json.loads(ci) if ci else [], image_uri=r["image_uri"],
            cached=edhrec.slugify(r["name"]) in cached,
        ))
    ql = q.lower()
    out.sort(key=lambda o: (not o.cached, not o.name.lower().startswith(ql), o.name))
    return out[:limit]
