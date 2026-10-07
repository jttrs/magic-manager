"""Explore surface of the typed API: one card (or two) as a card in the 99.

Adapts :mod:`magic_manager.explore` (the engine). The commander role is served by
:func:`magic_manager.api.edhrec.compare` with ``b`` optional.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .. import edhrec, explore, gallery
from .edhrec import OracleTagOut
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class CardOptionOut(BaseModel):
    name: str
    oracle_id: str | None
    type_line: str | None
    color_identity: list[str]
    image_uri: str | None
    cached: bool = Field(description="EDHREC card page already cached locally.")
    commander_eligible: bool


class FactsOut(BaseModel):
    oracle_id: str | None = None
    type_line: str | None = None
    cmc: float | None = None
    color_identity: list[str] = Field(default_factory=list)
    lowest_usd: float | None = None
    scryfall_id: str | None = None
    image_uri: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    scryfall_url: str | None = None
    owned: int = 0
    free: int = 0


class EntryOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    num_decks: int | None = None
    potential_decks: int | None = None
    share: float | None = Field(None, description="% of the potential decks that run it.")
    lift: float | None = Field(None, description="Co-play: how many times more often than chance.")
    group: str | None = Field(None, description="Co-play type group, or 'top'/'new' for commanders.")


class CardProfileOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    commander_eligible: bool
    num_decks: int | None
    potential_decks: int | None
    salt: float | None
    functions: list[str]
    tags: list[OracleTagOut]
    commanders: list[EntryOut]
    coplayed: list[EntryOut]
    similar: list[EntryOut]
    deck_mix: list[dict]


class PairedOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    bucket: Literal["a_only", "both", "b_only"]
    a: EntryOut | None
    b: EntryOut | None
    gap: float | None


class CardExploreOut(BaseModel):
    a: CardProfileOut
    b: CardProfileOut | None = None
    commanders: list[PairedOut] = Field(default_factory=list, description="Comparison only: by share.")
    coplayed: list[PairedOut] = Field(default_factory=list, description="Comparison only: by lift.")
    tags: dict[str, list[OracleTagOut]] = Field(default_factory=dict, description="Comparison only: a_only / both / b_only.")


def _facts(f: explore.Facts) -> FactsOut:
    return FactsOut(**asdict(f), scryfall_url=gallery.scryfall_card_url(f.set_code, f.collector_number) if f.set_code else None)


def _entry(e: explore.Entry) -> EntryOut:
    d = asdict(e)
    d["facts"] = _facts(e.facts)
    return EntryOut(**d)


def _profile(p: explore.CardProfile) -> CardProfileOut:
    return CardProfileOut(
        name=p.name, slug=p.slug, facts=_facts(p.facts), commander_eligible=p.commander_eligible,
        num_decks=p.num_decks, potential_decks=p.potential_decks, salt=p.salt,
        functions=p.functions, tags=[OracleTagOut(**t) for t in p.tags],
        commanders=[_entry(e) for e in p.commanders], coplayed=[_entry(e) for e in p.coplayed],
        similar=[_entry(e) for e in p.similar], deck_mix=p.deck_mix,
    )


def _paired(p: explore.Paired) -> PairedOut:
    return PairedOut(name=p.name, slug=p.slug, facts=_facts(p.facts), bucket=p.bucket,
                     a=_entry(p.a) if p.a else None, b=_entry(p.b) if p.b else None, gap=p.gap)


def search(q: str, *, limit: int = 20) -> list[CardOptionOut]:
    return [CardOptionOut(**c) for c in explore.search_cards(q, limit=limit)]


def card(a: str, b: str | None = None) -> CardExploreOut:
    if not b:
        return CardExploreOut(a=_profile(explore.card_profile(a)))
    c = explore.compare_cards(a, b)
    return CardExploreOut(
        a=_profile(c.a), b=_profile(c.b),
        commanders=[_paired(p) for p in c.commanders], coplayed=[_paired(p) for p in c.coplayed],
        tags={k: [OracleTagOut(**t) for t in v] for k, v in c.tags.items()},
    )


# ---------- rankings ----------

RankingScope = Literal["commanders", "cards", "salt"]


class RankingQuery(BaseModel):
    """One EDHREC ranking. Filters narrow COMMANDER rankings and don't stack:
    at most one of ``color`` / ``tag`` / ``set_family``."""
    scope: RankingScope = "commanders"
    timeframe: Literal["week", "month", "year"] = Field("week", description="Ignored by salt, tag and set rankings.")
    color: str | None = Field(None, description="Color identity: WUBRG letters or an EDHREC name (azorius, mono-red…).")
    tag: str | None = Field(None, description="Creature type or theme, e.g. goblins, treasure.")
    set_family: str | None = Field(None, description="Set family anchor or name, e.g. fin.")

    @model_validator(mode="after")
    def _one_filter(self):
        n = sum(bool(x) for x in (self.color, self.tag, self.set_family))
        if n > 1:
            raise ValueError("color, tag and set filters don't stack — pick one")
        if n and self.scope != "commanders":
            raise ValueError("filters apply only to commander rankings")
        return self

    def args(self) -> dict:
        return dict(color=self.color or None, tag=self.tag or None, set_family=self.set_family or None)


class RankedOut(BaseModel):
    rank: int | None
    name: str
    slug: str
    facts: FactsOut
    num_decks: int | None = None
    salt: float | None = Field(None, description="Average 0–4 'unfun to play against' rating (salt rankings).")
    trend: float | None = Field(None, description="EDHREC trend z-score.")


class RankingOut(BaseModel):
    scope: RankingScope
    timeframe: str = Field(description="Stored timeframe: week|month|year, 'all' (salt, tag) or '' (set).")
    filter: str = Field(description="'' | color:<slug> | tag:<slug> | set:<anchor>.")
    title: str
    cached: bool = Field(description="False = never fetched; run the edhrec.rankings job.")
    fetched_at: str | None
    rows: list[RankedOut]


class ColorOptionOut(BaseModel):
    slug: str
    label: str
    colors: str = Field(description="WUBRG identity letters ('' = colorless).")


class RankingOptionsOut(BaseModel):
    timeframes: list[str]
    colors: list[ColorOptionOut]
    tags: list[str] = Field(description="Tags already fetched (suggestions).")


def ranking(q: RankingQuery) -> RankingOut:
    r = explore.ranking(q.scope, q.timeframe, **q.args())
    return RankingOut(
        scope=r.key.scope, timeframe=r.key.timeframe, filter=r.key.filter, title=r.title,
        cached=r.cached, fetched_at=r.fetched_at,
        rows=[RankedOut(rank=x.rank, name=x.name, slug=x.slug, facts=_facts(x.facts),
                        num_decks=x.num_decks, salt=x.salt, trend=x.trend) for x in r.rows],
    )


def ranking_options() -> RankingOptionsOut:
    o = explore.ranking_options()
    return RankingOptionsOut(timeframes=o["timeframes"], colors=[ColorOptionOut(**c) for c in o["colors"]], tags=o["tags"])


class SyncRankingInput(RankingQuery):
    refresh: bool = Field(True, description="Re-fetch even when cached.")


def _run_sync_ranking(inp: SyncRankingInput, progress: ProgressFn) -> JobResult:
    progress(ProgressEvent(0, None, "Reading EDHREC…"))

    def tick(done: int, total: int, msg: str) -> None:
        progress(ProgressEvent(done, total, msg))

    res = edhrec.rankings(inp.scope, inp.timeframe, refresh=inp.refresh, progress=tick, **inp.args())
    return JobResult(summary=f"{res.name}: {len(res.rows)} entries", artifacts=[
        Artifact(kind="json", label="ranking", data={"title": res.name, "rows": len(res.rows), "fetched_at": res.fetched_at}),
    ])


SYNC_RANKING = register(JobSpec(
    name="edhrec.rankings",
    title="Fetch an EDHREC ranking",
    description="Top commanders (optionally by colour, tag or set), top cards, or the saltiest cards.",
    input_model=SyncRankingInput,
    run=_run_sync_ranking,
))
