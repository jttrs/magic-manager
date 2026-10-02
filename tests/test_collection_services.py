"""Phase 2 — the three non-ManaBox services (moxfield / archidekt / mtggoldfish).

Each is just a declarative config block over the shared engine; these tests
assert (a) read_csv maps each service's REAL export header correctly (fixtures
are actual exports captured 2026-10-02), (b) the resolve tiers behave — id-tier
for archidekt/mtggoldfish, (set,cn)-tier for moxfield, and (c) the error-
bisection quarantines a bad set code (MTGGoldfish PRM-* pseudo-sets) instead of
sinking the batch. The network boundary is monkeypatched; no HTTP.
"""

from __future__ import annotations

from pathlib import Path

from magic_manager import collection_sync as cs
from magic_manager import config as config_mod
from magic_manager import scryfall

FIXTURES = Path(__file__).parent / "fixtures" / "collection"


# ---------- config blocks load with the expected shape ----------

def test_all_four_services_configured():
    fmts = config_mod.collection_formats()
    assert set(fmts) >= {"manabox", "moxfield", "archidekt", "mtggoldfish"}
    # Only Moxfield is id-less; mtggoldfish is the one low-confidence service.
    assert fmts["moxfield"]["has_scryfall_id"] is False
    assert fmts["archidekt"]["has_scryfall_id"] is True
    assert fmts["mtggoldfish"]["confidence"] == "low"


# ---------- read_csv against the REAL export headers ----------

def test_read_moxfield_real_export():
    rows = cs.read_csv(FIXTURES / "moxfield_sample.csv", "moxfield")
    # 3 rows incl. the Yuna binder DUPLICATE (two identical pw25/16 foil rows).
    assert len(rows) == 3
    lightning = next(r for r in rows if r.name.startswith("Lightning"))
    assert lightning.set == "fin" and lightning.collector_number == "233"
    assert lightning.finish == "nonfoil"       # empty Foil cell → nonfoil
    assert lightning.scryfall_id is None        # Moxfield carries no id
    assert lightning.condition == "near_mint"   # "Near Mint" → near_mint
    yunas = [r for r in rows if r.name.startswith("Yuna")]
    assert len(yunas) == 2 and all(r.finish == "foil" for r in yunas)


def test_read_archidekt_both_variants_equivalent():
    # The default and all-fields exports differ in trailing columns only; the
    # mapped fields must come out identical.
    a = cs.read_csv(FIXTURES / "archidekt_sample.csv", "archidekt")
    b = cs.read_csv(FIXTURES / "archidekt_default_sample.csv", "archidekt")
    key = lambda rows: sorted((r.name, r.set, r.collector_number, r.finish,
                               r.scryfall_id, r.condition) for r in rows)
    assert key(a) == key(b)
    light = next(r for r in a if r.name.startswith("Lightning"))
    assert light.scryfall_id == "1103da9c-300c-406b-997d-9e5bb7cd02d6"
    assert light.finish == "nonfoil"            # "Normal" → nonfoil
    assert light.condition == "near_mint"       # "NM" → near_mint


def test_read_mtggoldfish_real_export():
    rows = cs.read_csv(FIXTURES / "mtggoldfish_sample.csv", "mtggoldfish")
    assert len(rows) == 2
    light = next(r for r in rows if r.name.startswith("Lightning"))
    assert light.finish == "nonfoil"            # "regular" → nonfoil
    assert light.scryfall_id == "1103da9c-300c-406b-997d-9e5bb7cd02d6"
    # The PRM-WPN promo: no id, non-Scryfall set code (lowercased), internal CN.
    yuna = next(r for r in rows if r.name.startswith("Yuna"))
    assert yuna.scryfall_id is None
    assert yuna.set == "prm-wpn" and yuna.collector_number == "1"


# ---------- resolve tiers ----------

def test_moxfield_resolves_via_setcn_tier(tmp_db, make_card, monkeypatch):
    # No scryfall_id on moxfield rows → the (set, cn) identifier must be used.
    card = make_card(id="sid-light", name="Lightning, Army of One",
                     set="fin", collector_number="233")
    captured = {}

    def fake_collection(idents):
        idents = list(idents)
        captured["idents"] = idents
        # Serve the card for a (set, cn) identifier.
        if any(i.get("set") == "fin" and i.get("collector_number") == "233" for i in idents):
            return [card], []
        return [], list(idents)

    monkeypatch.setattr(scryfall, "collection", fake_collection)
    rows = [cs.CollectionRow(qty=1, finish="nonfoil", set="fin",
                             collector_number="233", name="Lightning, Army of One")]
    res = cs.resolve_rows(rows)
    assert len(res.resolved) == 1
    assert res.resolved[0].scryfall_id == "sid-light"
    # The identifier sent was set+cn, not an id.
    assert captured["idents"] == [{"set": "fin", "collector_number": "233"}]


def test_bad_set_code_is_quarantined_not_fatal(tmp_db, make_card, monkeypatch):
    # One good (set,cn) + one bad set code that 400s. Bisection must resolve the
    # good row and report the bad one as not_found — never raise.
    good = make_card(id="sid-good", name="Good", set="fin", collector_number="233")

    def fake_collection(idents):
        idents = list(idents)
        if any(i.get("set") == "prm-wpn" for i in idents):
            raise scryfall.ScryfallError("HTTP 400: bad set code")
        hits = [good for i in idents if i.get("set") == "fin"]
        return hits, [i for i in idents if i.get("set") != "fin"]

    monkeypatch.setattr(scryfall, "collection", fake_collection)
    rows = [
        cs.CollectionRow(qty=1, finish="nonfoil", set="fin", collector_number="233", name="Good"),
        cs.CollectionRow(qty=1, finish="nonfoil", set="prm-wpn", collector_number="1", name="Bad Promo"),
    ]
    res = cs.resolve_rows(rows)  # must NOT raise
    assert [r.name for r in res.resolved] == ["Good"]
    assert len(res.not_found) == 1 and res.not_found[0]["name"] == "Bad Promo"


def test_safe_collection_bisects_to_isolate_culprit(monkeypatch):
    # Direct test of the bisection helper: 4 idents, 1 bad → the bad one isolated,
    # the other 3 found, with no exception escaping.
    def fake_collection(idents):
        idents = list(idents)
        if any(i.get("set") == "bad" for i in idents):
            raise scryfall.ScryfallError("400")
        return [{"id": i["set"]} for i in idents], []

    monkeypatch.setattr(scryfall, "collection", fake_collection)
    idents = [{"set": "a"}, {"set": "b"}, {"set": "bad"}, {"set": "d"}]
    found, not_found, errored = cs._safe_collection(idents)
    assert {c["id"] for c in found} == {"a", "b", "d"}
    assert errored == [{"set": "bad"}]
