"""Add-cards engine: search printings, resolve pasted/fetched lists to exact
printings, commit picks to inventory through one ingest event, list/add precons.

Single source of truth behind :mod:`magic_manager.api.ingest` (web) — the API
layer only adapts these return dicts to Pydantic models.
"""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Iterable

from . import (
    collection_view, db, decks, ingest, inventory, mtgjson, parsers, scryfall,
    selectors as sel_mod, treatments, util,
)

_CAND_CAP = 60
_CHUNK = 300
_IMPORT_DECK = Path(__file__).resolve().parent.parent.parent / "scripts" / "import_deck.py"
_SKIP_BOARDS = {"maybe", "maybeboard", "considering"}
_METHOD = {"search": "adhoc", "paste": "import-block", "deck": "import-block"}


# ---------- local card rows → printing dicts ----------

def _chunks(items: list, n: int = _CHUNK) -> Iterable[list]:
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _load(where: str, params: list | tuple = (), *, conn=None, limit: int | None = None) -> list[dict]:
    """Local ``cards`` rows matching ``where`` as card dicts (``_card_dict`` plus
    ``finishes``/``image_uri``/``released_at``/``is_promo``)."""
    sql = (
        f"SELECT {sel_mod._CARD_COLS}, c.image_uri AS c_image_uri, c.released_at AS c_released_at "
        f"FROM cards c WHERE {where}" + (f" LIMIT {int(limit)}" if limit else "")
    )
    if conn is None:
        with db.connect() as c:
            rows = c.execute(sql, params).fetchall()
    else:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        card = sel_mod._card_dict(r)
        card["finishes"] = r["finishes"]
        card["image_uri"] = r["c_image_uri"]
        card["released_at"] = r["c_released_at"]
        card["is_promo"] = r["is_promo"]
        out.append(card)
    return out


def _load_ids(sids: Iterable[str]) -> dict[str, dict]:
    ids = list(dict.fromkeys(sids))
    out: dict[str, dict] = {}
    for part in _chunks(ids):
        for c in _load(f"c.scryfall_id IN ({','.join('?' * len(part))})", part):
            out[c["scryfall_id"]] = c
    return out


def _physical(card: dict) -> bool:
    return not card.get("is_token") and not sel_mod._is_digital_only(card)


def _owned_by(sids: list[str]) -> dict[str, dict[str, int]]:
    owned: dict[str, dict[str, int]] = {}
    with db.connect() as conn:
        for part in _chunks(sids):
            rows = conn.execute(
                f"SELECT scryfall_id, finish, quantity FROM inventory "
                f"WHERE quantity > 0 AND scryfall_id IN ({','.join('?' * len(part))})", part,
            )
            for sid, fin, q in rows:
                owned.setdefault(sid, {})[fin] = q
    return owned


def _set_names() -> dict[str, str]:
    try:
        return {s["code"].lower(): s.get("name") for s in scryfall.all_sets()}
    except scryfall.ScryfallError:
        return {}


def _printings(cards: Iterable[dict]) -> dict[str, dict]:
    """PrintingOut-shaped dicts keyed by scryfall_id (one batched owned query)."""
    cards = list(cards)
    owned = _owned_by([c["scryfall_id"] for c in cards])
    names = _set_names()
    out = {}
    for c in cards:
        sid = c["scryfall_id"]
        code = (c.get("set") or "").lower()
        out[sid] = {
            "scryfall_id": sid, "oracle_id": c.get("oracle_id"), "name": c.get("name") or "",
            "set_code": code, "set_name": names.get(code),
            "collector_number": c.get("collector_number") or "",
            "rarity": c.get("rarity") or "common",
            "finishes": collection_view.inventory_finishes(c.get("finishes")),
            "treatment": treatments.compute_treatment(c, finish=None),
            "image_uri": c.get("image_uri"),
            "price_usd": c.get("prices_usd"), "price_usd_foil": c.get("prices_usd_foil"),
            "released_at": c.get("released_at"),
            "owned": owned.get(sid, {}),
        }
    return out


def _upsert(cards: list[dict]) -> None:
    if cards:
        with db.connect() as conn:
            db.upsert_cards(conn, cards)


def _newest_first(cards: list[dict]) -> list[dict]:
    """Stable: newest release first, then set, then collector number."""
    cards = sorted(cards, key=lambda c: ((c.get("set") or ""), util.cn_sort_key(c.get("collector_number"))))
    return sorted(cards, key=lambda c: c.get("released_at") or "", reverse=True)


# ---------- 1. search ----------

def _name_keys(c: dict) -> list[str]:
    return [k for k in ((c.get("name") or "").lower(), (c.get("flavor_name") or "").lower()) if k]


def _rank(cards: list[dict], q: str) -> list[dict]:
    ql = q.lower()

    def tier(c: dict) -> int:
        keys = _name_keys(c)
        if ql in keys:
            return 0
        return 1 if any(k.startswith(ql) for k in keys) else 2

    return sorted(_newest_first(cards), key=lambda c: (tier(c), (c.get("name") or "").lower()))


def search_printings(q: str, *, limit: int = 60) -> dict:
    q = q.strip()
    esc = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{esc}%"
    local = [c for c in _load(
        "(lower(c.name) LIKE ? ESCAPE '\\' OR lower(c.flavor_name) LIKE ? ESCAPE '\\')",
        (like, like), limit=5000,
    ) if _physical(c)]
    source = "local"
    if not local:
        source = "scryfall"
        try:
            found = list(itertools.islice(scryfall.search(f"{q} unique:prints game:paper"), limit))
        except scryfall.ScryfallError:
            found = []
        _upsert(found)
        local = [c for c in _load_ids(f["id"] for f in found).values() if _physical(c)]
    top = _rank(local, q)[:limit]
    built = _printings(top)
    return {"query": q, "source": source, "printings": [built[c["scryfall_id"]] for c in top]}


# ---------- shared resolver ----------

def _find_by_set_cn(pairs: set[tuple[str, str]]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for part in _chunks(sorted(pairs)):
        where = " OR ".join("(c.set_code = ? AND c.collector_number = ?)" for _ in part)
        for c in _load(where, [v for p in part for v in p]):
            out[((c.get("set") or "").lower(), (c.get("collector_number") or "").lower())] = c
    return out


_FRONT = "CASE WHEN instr(c.name, ' // ') > 0 THEN substr(c.name, 1, instr(c.name, ' // ') - 1) ELSE c.name END"


def _find_by_names(names: set[str]) -> dict[str, list[dict]]:
    """lower(name) → physical printings whose name, front face or flavor name equals it."""
    out: dict[str, list[dict]] = {}
    for part in _chunks(sorted(names)):
        ph = ",".join("?" * len(part))
        where = f"(lower(c.name) IN ({ph}) OR lower({_FRONT}) IN ({ph}) OR lower(c.flavor_name) IN ({ph}))"
        for c in _load(where, part * 3):
            if not _physical(c):
                continue
            name = (c.get("name") or "").lower()
            for k in {name, name.split(" // ")[0], (c.get("flavor_name") or "").lower()}:
                if k in part:
                    out.setdefault(k, []).append(c)
    return out


def _fetch_missing_names(names: set[str], display: dict[str, str]) -> None:
    """Rare path: learn oracle ids via ONE collection call, then pull prints."""
    if not names:
        return
    found, _ = scryfall.collection([{"name": display[n]} for n in sorted(names)])
    _upsert(found)
    for oid in dict.fromkeys(c.get("oracle_id") for c in found if c.get("oracle_id")):
        try:
            prints = list(itertools.islice(scryfall.search(f"oracleid:{oid} unique:prints game:paper"), 500))
        except scryfall.ScryfallError:
            continue
        _upsert(prints)


def _resolve_wants(wants: list[dict]) -> tuple[list[dict], list[str]]:
    """Resolve want dicts (qty, name, set, cn, sid, finish, raw, section, line) to
    ResolvedLineOut dicts. Batched: local queries first, then at most one
    ``collection`` call per identifier kind."""
    warnings: list[str] = []

    # exact ids
    by_id = _load_ids(w["sid"] for w in wants if w.get("sid"))
    miss = [w["sid"] for w in wants if w.get("sid") and w["sid"] not in by_id]
    if miss:
        found, _ = scryfall.collection([{"id": s} for s in dict.fromkeys(miss)])
        _upsert(found)
        by_id.update(_load_ids(c["id"] for c in found))

    # set + collector number
    pairs = {(w["set"].lower(), w["cn"].lower()) for w in wants
             if not w.get("sid") and w.get("set") and w.get("cn")}
    by_cn = _find_by_set_cn(pairs)
    miss_pairs = [p for p in sorted(pairs) if p not in by_cn]
    if miss_pairs:
        found, _ = scryfall.collection([{"set": s, "collector_number": n} for s, n in miss_pairs])
        _upsert(found)
        by_cn = _find_by_set_cn(pairs)

    def exact_card(w: dict) -> dict | None:
        if w.get("sid"):
            return by_id.get(w["sid"])
        if w.get("set") and w.get("cn"):
            return by_cn.get((w["set"].lower(), w["cn"].lower()))
        return None

    # names (everything not resolved exactly)
    need = {w["name"].lower(): w["name"] for w in wants if exact_card(w) is None and w.get("name")}
    by_name = _find_by_names(set(need))
    missing = {n for n in need if n not in by_name}
    if missing:
        _fetch_missing_names(missing, need)
        by_name.update(_find_by_names(missing))

    # printing dicts for everything referenced (one owned query)
    ref: dict[str, dict] = {}
    for c in itertools.chain(by_id.values(), by_cn.values(), itertools.chain.from_iterable(by_name.values())):
        ref[c["scryfall_id"]] = c
    printings = _printings(ref.values())

    def best_first(cards: list[dict]) -> list[dict]:
        cards = list({c["scryfall_id"]: c for c in cards}.values())
        cards = _newest_first(cards)

        def key(c: dict) -> tuple:
            promo = bool(json.loads(c.get("promo_types") or "[]")) or bool(c.get("is_promo"))
            std = treatments.is_standard_frame(c) and not promo
            return (-sum(printings[c["scryfall_id"]]["owned"].values()), not std)

        return sorted(cards, key=key)[:_CAND_CAP]

    lines: list[dict] = []
    for w in wants:
        line = {
            "line": w.get("line", 0), "raw": w["raw"], "qty": w["qty"], "name": w["name"],
            "finish": w["finish"], "section": w["section"], "status": "unresolved",
            "candidates": [], "chosen": None, "note": None,
        }
        card = exact_card(w)
        cands: list[dict] = []
        if card is not None:
            cands = [card]
            if w.get("name") and not parsers.name_matches_card(w["name"], card):
                warnings.append(
                    f"name/printing mismatch: {w['raw']!r} resolved to {card.get('name')!r} via "
                    f"({card.get('set')}) {card.get('collector_number')}"
                )
        else:
            named = by_name.get((w.get("name") or "").lower(), [])
            if w.get("set"):
                in_set = [c for c in named if (c.get("set") or "").lower() == w["set"].lower()]
                named = in_set or named
            cands = best_first(named)
            if w.get("set") and w.get("cn") and cands:
                line["note"] = f"No printing ({w['set'].upper()}) {w['cn']} — pick a printing"
        if not cands:
            line["note"] = f"No card named {w['name']!r}"
            lines.append(line)
            continue
        line["status"] = "exact" if len(cands) == 1 else "ambiguous"
        line["candidates"] = [printings[c["scryfall_id"]] for c in cands]
        chosen = line["candidates"][0]
        line["chosen"] = chosen["scryfall_id"]
        if line["finish"] not in chosen["finishes"]:
            switched = chosen["finishes"][0]
            note = f"No {line['finish']} printing — switched to {switched}"
            line["note"] = f"{line['note']}; {note}" if line["note"] else note
            line["finish"] = switched
        lines.append(line)
    return lines, warnings


# ---------- 2. resolve pasted text ----------

def resolve_text(text: str, *, fmt: str = "auto") -> dict:
    parsed = parsers.parse_text(text)
    wants = [{
        "line": e.line_no, "raw": e.raw, "qty": e.qty, "name": e.name, "set": e.set,
        "cn": e.collector_number, "finish": "foil" if e.foil else "nonfoil", "section": e.section,
    } for e in parsed.entries]
    lines, warnings = _resolve_wants(wants)
    detected = parsers.detect_paste_format(text)
    return {
        "format": detected if fmt == "auto" else fmt,
        "lines": lines, "warnings": list(parsed.warnings) + warnings, "deck_name": None,
    }


# ---------- 3. commit ----------

def commit(items: list[tuple[str, str, int]], *, source: str, label: str | None = None) -> dict:
    merged: dict[tuple[str, str], int] = {}
    for sid, finish, qty in items:
        merged[(sid, finish)] = merged.get((sid, finish), 0) + qty
    cards = _load_ids(sid for sid, _ in merged)
    unknown = sorted({sid for sid, _ in merged if sid not in cards})
    if unknown:
        raise LookupError(f"unknown scryfall_id(s): {', '.join(unknown)}")
    for sid, finish in merged:
        if finish not in collection_view.inventory_finishes(cards[sid].get("finishes")):
            raise LookupError(f"{cards[sid].get('name')} ({sid}) has no {finish} finish")
    method = _METHOD[source]
    event_label = f"web:{source}" + (f" · {label}" if label else "")
    with ingest.open_ingest_event(method, label=event_label) as rec:
        for (sid, finish), qty in merged.items():
            inventory.inventory_add(sid, finish, qty, conn=rec.conn, ingest_id=rec.ingest_id, method=method)
    copies = sum(merged.values())
    printings = len({sid for sid, _ in merged})
    return {
        "ingest_id": rec.ingest_id, "copies": copies, "printings": printings,
        "summary": f"+{copies} copies · {printings} printings",
    }


# ---------- 4. precon catalog ----------

def precon_catalog(q: str = "", *, limit: int = 50) -> list[dict]:
    tokens = q.lower().split()
    rows = []
    for d in mtgjson.deck_list():
        if (d.get("type") or "") not in mtgjson.PRECON_MODERN_TYPES:
            continue
        if mtgjson._is_collector_edition(d.get("name") or ""):
            continue
        hay = " ".join(str(d.get(k) or "") for k in ("name", "code", "type")).lower()
        if all(t in hay for t in tokens):
            rows.append(d)
    rows.sort(key=lambda d: d.get("name") or "")
    rows.sort(key=lambda d: d.get("releaseDate") or "", reverse=True)
    rows = rows[:limit]
    counts = decks.precon_unit_counts()
    out = []
    for d in rows:
        built, decon = counts.get(d["fileName"], (0, 0))
        out.append({
            "file_name": d["fileName"], "name": d.get("name") or d["fileName"],
            "set_code": (d.get("code") or "").lower(), "type": d.get("type") or "",
            "release_date": d.get("releaseDate"),
            "default_state": mtgjson.default_precon_state(d["fileName"], name=d.get("name")),
            "owned_built": built, "owned_deconstructed": decon,
        })
    return out


# ---------- 5. add precon ----------

def add_precon(file_name: str, *, copies: int = 1, state: str = "auto") -> dict:
    from . import sets as sets_mod  # local import avoids a module-level cycle

    if state == "auto":
        state = mtgjson.default_precon_state(file_name)
    row = parsers.JumpstartRow(
        file_name=file_name, theme="",
        keep_qty=copies if state == "built" else 0,
        deconstructed_qty=copies if state != "built" else 0,
    )
    res = sets_mod._apply_precon_checklist(
        parsers.JumpstartParseResult(rows=[row], warnings=[], meta={"kind": "precon", "mode": "add"}),
        mode="add",
    )
    per_row = res["per_row"][0] if res["per_row"] else {}
    if per_row.get("error"):
        raise RuntimeError(per_row["error"])
    name = per_row.get("label") or file_name
    cards = res["inv_qty_total"]
    return {
        "summary": f"Added {name} ×{copies} · {cards} cards · {state}",
        "file_name": file_name, "name": name, "state": state, "copies": copies,
        "cards": cards, "slugs": per_row.get("slugs", []),
        "missing_sids": per_row.get("missing_sids", []),
        "warning": per_row.get("warning"),
    }


# ---------- 6. fetch a deck URL ----------

def fetch_deck_lines(url: str, *, progress: Callable[[str], None] | None = None) -> dict:
    proc = subprocess.Popen(
        [sys.executable, str(_IMPORT_DECK), url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    err_lines: list[str] = []

    def _pump() -> None:
        for raw in proc.stderr:
            msg = raw.rstrip()
            if msg:
                err_lines.append(msg)
                if progress:
                    progress(msg)

    t = threading.Thread(target=_pump, daemon=True)
    t.start()
    out = proc.stdout.read()
    proc.wait()
    t.join()
    if proc.returncode != 0:
        raise RuntimeError(err_lines[-1] if err_lines else f"import_deck exited {proc.returncode}")
    payload = json.loads(out)
    wants = []
    for c in payload.get("cards", []):
        if (c.get("board") or "") in _SKIP_BOARDS:
            continue
        name = c.get("name") or ""
        wants.append({
            "line": 0, "raw": f"{c['qty']} {name}", "qty": c["qty"], "name": name,
            "sid": c.get("scryfall_id"), "set": c.get("set"), "cn": c.get("collector_number"),
            "finish": "foil" if c.get("finish") == "foil" else "nonfoil",
            "section": c.get("board") or "main",
        })
    lines, warnings = _resolve_wants(wants)
    return {"format": "deck", "lines": lines, "warnings": warnings, "deck_name": payload.get("name")}
