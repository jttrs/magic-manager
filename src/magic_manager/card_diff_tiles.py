"""Card-diff → gallery tiles: the single home for turning ``card_diff`` pools into
deduped, image-carrying, buy-list-annotated tile dicts.

Lifted verbatim from ``scripts/card_diff_html.py`` so every delivery surface (the
self-contained HTML gallery script AND the web API) shares one adapter instead of
copying it. Missing-set views show EXACT printings, so tiles keep the precise
``scryfall_id`` / finish of each pool row.
"""
from __future__ import annotations

from . import db, exports, gallery, util
from .gallery import ExportSpec, PoolSpec, scryfall_card_url

POOL_CHOICES = ("printing", "functional", "variant-chase")
# The three card-diff pools, each mapped to the CSS color var it renders with.
POOLS = [
    PoolSpec("printing", "Printing", "info"),
    PoolSpec("functional", "Functional", "warning"),
    PoolSpec("variant-chase", "Variant-chase", "accent"),
]
_POOL_BY_KEY = {p.key: p for p in POOLS}
# "Copy the shown tiles" buy-list buttons (payloads live on each tile's
# data-mp / data-tcg attributes, built via the one exports engine).
_EXPORTS = [
    ExportSpec("copy-mp", "ManaPool", "mp"),
    ExportSpec("copy-tcg", "TCGplayer", "tcg"),
]


def _tile_from_materialized(r, pool: str, family_code: str, images: dict) -> dict:
    """Normalize a MaterializedRow (printing / variant-chase pool) into a tile
    dict the renderer understands. ``pools`` starts as a one-element set; the
    caller unions further pool membership onto it during dedup."""
    c = r.card
    finish = r.finish
    unit = c.get("prices_usd_foil") if finish == "foil" else c.get("prices_usd")
    usd = (unit * r.quantity) if unit is not None else None
    set_code = c.get("set")
    cn = c.get("collector_number")
    return {
        "sid_key": ("sid", r.scryfall_id),
        "pools": {pool},
        "family": family_code,
        "name": c.get("name") or "",
        "set": (set_code or "").upper(),
        "cn": cn,
        "rarity": c.get("rarity"),
        "finish": finish,
        "usd": usd,
        "image_uri": images.get(("sid", r.scryfall_id)),
        "scryfall_url": scryfall_card_url(set_code, cn),
        "row": r,  # source MaterializedRow — for exports.build (buy-list lines)
    }


class _ExportRow:
    """Minimal MaterializedRow stand-in so a FunctionalMissingCard can feed
    ``exports.build`` (which reads ``.card`` / ``.finish`` / ``.quantity``). The
    functional pool's representative printing is the cheapest in-family one; its
    full ``cards``-table row is fetched once in ``build_tiles`` and attached here
    so the TCGplayer formatter (treatment suffix + collision prefix) has the
    fields it needs — same as a printing-pool row."""
    __slots__ = ("card", "finish", "quantity", "scryfall_id")

    def __init__(self, card: dict, finish: str):
        self.card = card
        self.finish = finish or "nonfoil"
        self.quantity = 1
        self.scryfall_id = card.get("scryfall_id")


def _tile_from_functional(c, family_code: str, images: dict) -> dict:
    """Normalize a FunctionalMissingCard (functional pool) into a tile dict.
    Functional cards carry no scryfall_id of their own; the caller resolves
    one via (set_code, family_cn) so this tile can merge with a printing/
    variant-chase tile of the same underlying printing."""
    set_code = c.set_code
    cn = c.family_cn
    image_uri = None
    sid = None
    card_dict = None
    if set_code and cn:
        setcn_key = (set_code.lower(), cn)
        image_uri = images.get(("setcn-img", setcn_key))
        sid = images.get(("setcn-sid", setcn_key))
        card_dict = images.get(("setcn-card", setcn_key))
    sid_key = ("sid", sid) if sid else ("fn", set_code or "", cn or "")
    # Row for exports.build (buy-list lines); None when the printing has no local
    # cards row (shouldn't happen — functional reps come from cards — but guard).
    row = _ExportRow(card_dict, c.family_finish) if card_dict else None
    return {
        "sid_key": sid_key,
        "pools": {"functional"},
        "family": family_code,
        "name": c.name or "",
        "set": (set_code or "").upper() if set_code else None,
        "cn": cn,
        "rarity": None,
        "finish": c.family_finish,
        "usd": c.family_usd,
        "image_uri": image_uri,
        "scryfall_url": scryfall_card_url(set_code, cn),
        "row": row,
    }


def _fetch_images(sids: set[str], setcns: set[tuple[str, str]]) -> dict:
    """ONE batched lookup of image_uri + scryfall_id, keyed by both access
    patterns the tiles need: ("sid", scryfall_id) for printing/variant-chase
    rows' image_uri; ("setcn-img", (set_code_lower, cn)) and
    ("setcn-sid", (set_code_lower, cn)) for functional cards (which carry no
    scryfall_id of their own but need both their image AND their scryfall_id
    so they can be deduped against a printing/variant-chase tile of the same
    printing)."""
    images: dict = {}
    if not sids and not setcns:
        return images
    with db.connect() as conn:
        if sids:
            placeholders = ",".join("?" for _ in sids)
            rows = conn.execute(
                f"SELECT scryfall_id, image_uri FROM cards WHERE scryfall_id IN ({placeholders})",
                list(sids),
            ).fetchall()
            for row in rows:
                images[("sid", row["scryfall_id"])] = row["image_uri"]
        if setcns:
            placeholders = ",".join("(?,?)" for _ in setcns)
            params = [p for pair in setcns for p in pair]
            rows = conn.execute(
                "SELECT scryfall_id, oracle_id, name, set_code, collector_number, "
                "rarity, prices_usd, prices_usd_foil, type_line, promo_types, "
                "frame_effects, border_color, full_art, finishes, image_uri "
                f"FROM cards WHERE (LOWER(set_code), collector_number) IN ({placeholders})",
                params,
            ).fetchall()
            for row in rows:
                key = ((row["set_code"] or "").lower(), row["collector_number"])
                images[("setcn-img", key)] = row["image_uri"]
                images[("setcn-sid", key)] = row["scryfall_id"]
                # Full card dict (set=lower, mirroring selectors' _card_dict) so a
                # functional tile can build a proper exports row for the buy-list.
                images[("setcn-card", key)] = {
                    "scryfall_id": row["scryfall_id"], "oracle_id": row["oracle_id"],
                    "name": row["name"], "set": (row["set_code"] or "").lower(),
                    "collector_number": row["collector_number"], "rarity": row["rarity"],
                    "prices_usd": row["prices_usd"], "prices_usd_foil": row["prices_usd_foil"],
                    "type_line": row["type_line"], "promo_types": row["promo_types"],
                    "frame_effects": row["frame_effects"], "border_color": row["border_color"],
                    "full_art": row["full_art"], "finishes": row["finishes"],
                }
    return images


def _attach_export_attrs(t: dict) -> None:
    """Pre-render the canonical ManaPool + TCGplayer buy-list lines for a tile
    (via the ONE exports engine — the TCGplayer formatter needs full-row context
    the DOM lacks: treatment-suffix product names + collision (NNNN) prefixes),
    stashing them on ``data_attrs`` for the gallery's "copy shown" buttons. A
    tile with no source row (rare: no local printing) gets empty attrs → skipped
    by the JS collector."""
    row = t.get("row")
    mp_line = tcg_line = ""
    if row is not None:
        mp_line = exports.build("manapool", [row]).strip()
        tcg_line = exports.build("tcgplayer", [row]).strip()
    t["data_attrs"] = {"mp": mp_line, "tcg": tcg_line}


def build_tiles(diffs: list, pools: list[str]) -> list[dict]:
    """Flatten every requested pool of every FamilyDiff into UNIQUE-printing
    tile dicts: one tile per distinct scryfall_id per family, each carrying
    the SET of pools it belongs to (deduped — a printing in both the
    printing and variant-chase pools renders ONCE with both pools unioned
    onto it). Deterministic order: family order from `diffs`, within-family
    by value desc then set/cn."""
    # Pre-pass: collect every id this run needs images for, ONE query.
    sids: set[str] = set()
    setcns: set[tuple[str, str]] = set()
    for fd in diffs:
        if "printing" in pools:
            sids |= {r.scryfall_id for r in fd.printing.rows}
        if "variant-chase" in pools:
            sids |= {r.scryfall_id for r in fd.variant_chase.rows}
        if "functional" in pools:
            setcns |= {
                (c.set_code.lower(), c.family_cn)
                for c in fd.functional.rows if c.set_code and c.family_cn
            }
    images = _fetch_images(sids, setcns)

    tiles: list[dict] = []
    for fd in diffs:
        raw: list[dict] = []
        if "printing" in pools:
            raw += [_tile_from_materialized(r, "printing", fd.code, images)
                    for r in fd.printing.rows]
        if "functional" in pools:
            raw += [_tile_from_functional(c, fd.code, images)
                    for c in fd.functional.rows]
        if "variant-chase" in pools:
            raw += [_tile_from_materialized(r, "variant-chase", fd.code, images)
                    for r in fd.variant_chase.rows]

        family_tiles = gallery.merge_tiles(raw)
        family_tiles.sort(key=gallery.tile_sort_key)
        for t in family_tiles:
            _attach_export_attrs(t)
        tiles.extend(family_tiles)
    return tiles


def family_summary(fd, pools: list[str]) -> str:
    """The per-family sub-header string: owned value + each pool's count·value."""
    pool_summary = " · ".join(
        f"{_POOL_BY_KEY[p].label} {getattr(fd, p.replace('-', '_')).count}·"
        f"{util.fmt_usd(getattr(fd, p.replace('-', '_')).usd)}"
        for p in pools
    )
    return f"owned {util.fmt_usd(fd.owned_usd)} · {pool_summary}"
