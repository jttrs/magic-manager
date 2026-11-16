"""sets.refresh_printing_prices: targeted re-reads of stale or pre-release prices."""
from __future__ import annotations

from magic_manager import db, scryfall, sets

STALE, FRESH, PREORDER = "a" * 36, "b" * 36, "c" * 36


def _stamp(sid: str, priced: str, released: str) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_updated_at = ?, released_at = ? WHERE scryfall_id = ?", (priced, released, sid))
        conn.commit()


def test_rereads_only_stale_or_preorder_prices(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([make_card(id=STALE, set="sld", collector_number="1", prices={"usd": "50.00"}),
                make_card(id=FRESH, set="sld", collector_number="2", prices={"usd": "5.00"}),
                make_card(id=PREORDER, set="sld", collector_number="3", prices={"usd": "47.91"})])
    _stamp(STALE, "2026-09-01T00:00:00+00:00", "2026-08-01")      # >7 days old
    _stamp(FRESH, "2026-11-14T00:00:00+00:00", "2026-08-01")      # fresh
    _stamp(PREORDER, "2026-11-10T00:00:00+00:00", "2026-11-12")   # read before release
    asked: list[str] = []

    def collection(identifiers, **_):
        ids = [i["id"] for i in identifiers]
        asked.extend(ids)
        cn = {STALE: "1", FRESH: "2", PREORDER: "3"}
        return [{**make_card(id=i, set="sld", collector_number=cn[i]), "prices": {"usd": "19.93"},
                 "released_at": "2026-11-12" if i == PREORDER else "2026-08-01"} for i in ids], []
    monkeypatch.setattr(scryfall, "collection", collection)

    out = sets.refresh_printing_prices([STALE, FRESH, PREORDER], today="2026-11-15")
    assert sorted(asked) == sorted([STALE, PREORDER])
    assert out["refreshed"] == 2 and out["preorder"] is False
    with db.connect() as conn:
        prices = dict(conn.execute("SELECT scryfall_id, prices_usd FROM cards"))
    assert prices[STALE] == 19.93 and prices[FRESH] == 5.0


def test_a_price_still_dated_before_release_is_flagged(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([make_card(id=PREORDER, set="sld", collector_number="3")])
    monkeypatch.setattr(scryfall, "collection", lambda ids, **_: ([], [{"id": PREORDER}]))   # Scryfall has nothing newer
    _stamp(PREORDER, "2026-11-10T00:00:00+00:00", "2026-11-12")
    assert sets.refresh_printing_prices([PREORDER], today="2026-11-11")["preorder"] is True
    assert sets.refresh_printing_prices([], today="2026-11-11") == {"refreshed": 0, "prices_at": None, "preorder": False}
