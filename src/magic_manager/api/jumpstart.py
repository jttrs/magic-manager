"""Jumpstart surface of the typed API (Collection → Jumpstart sheet).

Adapts :mod:`magic_manager.jumpstart`: a set's pack versions (theme, colour,
top card, value, your copies, how much your free cards cover), one pack's
cards, the two shopping lists, and the ``jumpstart.read`` job that fetches a
set's deck files the first time.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards, jumpstart, scryfall
from .ingest import PrintingOut
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register

Target = Literal["manapool", "tcgplayer", "cardkingdom"]


class JumpstartSetOut(BaseModel):
    code: str
    name: str
    released: str | None
    packs: int = Field(description="Pack versions.")
    themes: int
    owned_packs: int = Field(description="Versions you own at least one copy of (built or broken down).")


class JumpstartSetsOut(BaseModel):
    sets: list[JumpstartSetOut]


class JumpstartPackOut(BaseModel):
    file_name: str
    name: str
    theme: str
    version: int | None
    color: str = Field(description="WUBRG letters of the pack's cards; 'C' = colorless.")
    card_count: int
    usd_total: float | None = Field(description="Cards at their shipped finish plus the front card.")
    top_card: str | None
    top_card_usd: float | None
    front_card: str | None
    top_card_image: str | None = None
    built: int
    deconstructed: int
    deck_slug: str | None = Field(None, description="A deck row for this version you own (built first).")
    have: int = Field(description="Pack cards your free copies cover (each pack on its own).")
    short: int = Field(description="Pack cards you have no free copy for.")
    status: Literal["build", "close", "far"]


class JumpstartShopOut(BaseModel):
    cards: int
    copies: int
    usd: float


class JumpstartOut(BaseModel):
    code: str
    name: str
    ready: bool = Field(description="False = deck files not read yet; run the jumpstart.read job.")
    close_short: int = Field(jumpstart.CLOSE_SHORT, description="A pack this many cards short or fewer is 'close'.")
    packs: list[JumpstartPackOut] = Field(default_factory=list)
    themes: int = 0
    buildable: JumpstartShopOut | None = Field(None, description="Cards to make every theme buildable (one built copy of each + other versions' extras).")
    whole: JumpstartShopOut | None = Field(None, description="Every pack version you don't own, full contents.")
    whole_packs: int = 0


class JumpstartPackCardOut(BaseModel):
    printing: PrintingOut
    count: int
    foil: bool
    unit_usd: float | None
    free: int


class JumpstartPackDetailOut(BaseModel):
    pack: JumpstartPackOut
    cards: list[JumpstartPackCardOut]
    unknown: list[str] = Field(default_factory=list, description="Card names not in the local cards table.")


class JumpstartBuyIn(BaseModel):
    shop: jumpstart.Shop
    target: Target


class JumpstartBuyOut(BaseModel):
    text: str
    lines: int


def _set_names() -> dict[str, dict]:
    try:
        return {s["code"].lower(): s for s in scryfall.all_sets() if s.get("code")}
    except Exception:  # noqa: BLE001 — names are cosmetic; codes still work offline
        return {}


def _name(code: str, names: dict[str, dict]) -> str:
    return (names.get(code) or {}).get("name") or code.upper()


def sets() -> JumpstartSetsOut:
    names = _set_names()
    out: list[JumpstartSetOut] = []
    for code in jumpstart.jumpstart_set_codes():
        vs = jumpstart.variants(code)
        out.append(JumpstartSetOut(
            code=code, name=_name(code, names),
            released=(names.get(code) or {}).get("released_at") or (vs[0].get("releaseDate") if vs else None),
            packs=len(vs), themes=len({jumpstart.theme_of(v.get("name") or "") for v in vs}),
            owned_packs=len(jumpstart.owned_file_names(code)),
        ))
    out.sort(key=lambda s: s.released or "", reverse=True)
    return JumpstartSetsOut(sets=out)


def _pack(p: jumpstart.Pack, images: dict[str, str | None]) -> JumpstartPackOut:
    return JumpstartPackOut(file_name=p.file_name, name=p.name, theme=p.theme, version=p.version, color=p.color,
                            card_count=p.card_count, usd_total=p.usd_total, top_card=p.top_card,
                            top_card_usd=p.top_card_usd, top_card_image=images.get(p.top_card_id or ""),
                            front_card=p.front_card, built=p.built, deconstructed=p.deconstructed,
                            deck_slug=p.deck_slug, have=p.have, short=p.short, status=p.status)


def _images(packs: list[jumpstart.Pack]) -> dict[str, str | None]:
    pr = addcards.printings_for_ids(p.top_card_id for p in packs if p.top_card_id)
    return {sid: x.get("image_uri") for sid, x in pr.items()}


def _check(code: str) -> str:
    code = code.lower()
    if not jumpstart.variants(code):
        raise LookupError(f"{code.upper()} has no Jumpstart packs")
    return code


def view(code: str) -> JumpstartOut:
    code = _check(code)
    name = _name(code, _set_names())
    if not jumpstart.is_ready(code):
        return JumpstartOut(code=code, name=name, ready=False)
    packs = jumpstart.set_packs(code)
    images = _images(packs)
    b = jumpstart.buildable_missing(code)
    w = jumpstart.missing_packs(code)
    return JumpstartOut(
        code=code, name=name, ready=True, packs=[_pack(p, images) for p in packs],
        themes=len({p.theme for p in packs}),
        buildable=JumpstartShopOut(cards=len(b.rows), copies=b.copies, usd=b.usd),
        whole=JumpstartShopOut(cards=len(w.rows), copies=w.copies, usd=w.usd), whole_packs=len(w.packs),
    )


def pack(code: str, file_name: str) -> JumpstartPackDetailOut:
    code = _check(code)
    p = next((x for x in jumpstart.set_packs(code) if x.file_name == file_name), None)
    if p is None:
        raise LookupError(f"no pack {file_name!r} in {code.upper()}")
    printings = addcards.printings_for_ids(c.scryfall_id for c in p.cards)
    return JumpstartPackDetailOut(
        pack=_pack(p, _images([p])),
        cards=[JumpstartPackCardOut(printing=PrintingOut(**printings[c.scryfall_id]), count=c.count, foil=c.foil,
                           unit_usd=c.unit_usd, free=c.free)
               for c in p.cards if c.scryfall_id in printings],
        unknown=[c.name for c in p.cards if c.scryfall_id not in printings],
    )


def buy_list(code: str, req: JumpstartBuyIn) -> JumpstartBuyOut:
    text, lines = jumpstart.buy_text(_check(code), req.shop, req.target)
    return JumpstartBuyOut(text=text, lines=lines)


# ---------- job: read a set's packs the first time ----------

class ReadJumpstartInput(BaseModel):
    code: str = Field(min_length=2, max_length=8, description="Jumpstart set code, e.g. j25.")


def _run_read(inp: ReadJumpstartInput, progress: ProgressFn) -> JobResult:
    code = _check(inp.code)

    def tick(done: int, total: int, msg: str) -> None:
        progress(ProgressEvent(done=done, total=total, message=msg))

    n = jumpstart.ensure_ready(code, progress=tick)
    return JobResult(summary=f"{code.upper()}: read {n} packs",
                     artifacts=[Artifact(kind="json", label="jumpstart", data={"code": code, "packs": n})])


READ = register(JobSpec(
    name="jumpstart.read",
    title="Read a Jumpstart set's packs",
    description="Fetch every pack version's card list, fill card sets with no local prices, and the packs' front cards.",
    input_model=ReadJumpstartInput,
    run=_run_read,
))
