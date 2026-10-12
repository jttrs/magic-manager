"""Add cards → Import a collection, from another app's exported file.

Every fixture under ``tests/fixtures/collection`` is a real export header (see
``config/collection_formats.toml`` for each format's provenance). The file is
detected from its header, read into the same normalized lines the companion
sends, and goes through the SAME ``preview_lines`` / ``apply_lines`` path:
ONE ``collection-import`` event, add or replace chosen per import, unlisted
printings untouched, replace refused below built-deck copies. Fully offline.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import collection_sync as cs
from magic_manager import config, db, ingest, inventory, scryfall

FIX = Path(__file__).resolve().parent / "fixtures" / "collection"

# fixture → (detected service, lines, first line's (qty, finish, set, cn))
EXPECT = {
    "manabox_sample.csv": ("manabox", 3, (1, "nonfoil", "c21", "263")),
    "moxfield_sample.csv": ("moxfield", 3, (1, "nonfoil", "fin", "233")),
    "archidekt_sample.csv": ("archidekt", 2, (1, "nonfoil", "fin", "233")),
    "archidekt_default_sample.csv": ("archidekt", 2, (1, "nonfoil", "fin", "233")),
    "mtggoldfish_sample.csv": ("mtggoldfish", 2, (1, "nonfoil", "fin", "233")),
    "deckbox_sample.csv": ("deckbox", 2, (1, "nonfoil", "ltr", "192")),
    "dragonshield_sample.csv": ("dragonshield", 2, (1, "foil", "ltr", "741z")),     # quoted "sep=," + CRLF
    "tcgplayer_sample.csv": ("tcgplayer", 2, (1, "nonfoil", "ema", "225")),
    "delverlens_sample.csv": ("delverlens", 2, (1, "nonfoil", "pcy", "45")),
}


def test_new_formats_carry_their_identity_and_finish():
    deckbox = cs.read_export((FIX / "deckbox_sample.csv").read_text()).lines
    assert [(ln["scryfall_id"], ln["finish"]) for ln in deckbox] == [
        ("e98d5321-ec09-456c-a9ea-c8ca2cfc6205", "nonfoil"), ("5f092adf-a06e-47c1-9400-2eebf9ef719d", "foil")]
    ds = cs.read_export((FIX / "dragonshield_sample.csv").read_text()).lines
    assert [ln["finish"] for ln in ds] == ["foil", "nonfoil"]      # "Double Rainbow Foil" / "Normal"
    assert cs._finish_from(cs.service_format("dragonshield"), "Etched") == "foil"
    delver = cs.read_export((FIX / "delverlens_sample.csv").read_text()).lines
    assert [(ln["quantity"], ln["finish"]) for ln in delver] == [(1, "nonfoil"), (2, "foil")]


@pytest.mark.parametrize("name", sorted(EXPECT))
def test_every_fixture_is_detected_and_read(name):
    service, n, first = EXPECT[name]
    read = cs.read_export((FIX / name).read_text(encoding="utf-8-sig"))
    assert read.service == service
    assert read.name == cs.service_format(service)["app"]["name"]
    assert len(read.lines) == n
    ln = read.lines[0]
    assert (ln["quantity"], ln["finish"], ln["set"], ln["cn"]) == first


def test_every_collection_fixture_has_an_expectation():
    assert {p.name for p in FIX.glob("*.csv")} <= set(EXPECT)


def test_every_importable_format_declares_how_to_detect_it():
    for key, fmt in config.collection_formats().items():
        app = fmt.get("app") or {}
        assert app.get("name") and app.get("detect"), key


def test_detection_is_unambiguous_across_fixtures():
    # No fixture's header satisfies two services at the same specificity.
    for p in FIX.glob("*.csv"):
        have = {h.lower() for h in cs._header(p.read_text(encoding="utf-8-sig"))}
        hits = [(len(f["app"]["detect"]), k) for k, f in config.collection_formats().items()
                if all(h.lower() in have for h in f["app"]["detect"])]
        best = max(n for n, _ in hits)
        assert [k for n, k in hits if n == best] == [EXPECT[p.name][0]], p.name


def test_unknown_file_names_the_supported_apps():
    with pytest.raises(cs.UnknownFormat) as e:
        cs.read_export("Card,Qty\nSol Ring,1\n")
    assert "ManaBox" in str(e.value) and "Moxfield" in str(e.value)


def test_preamble_bom_semicolons_proxies_and_split_foil_counts(monkeypatch):
    fmts = dict(config.collection_formats())
    fmts["splitapp"] = {
        "app": {"name": "Split", "detect": ["Reg Qty", "Foil Qty", "Set Code"]},
        "columns": {"quantity": "Reg Qty", "foil_quantity": "Foil Qty", "set": "Set Code",
                    "collector_number": "Number", "name": "Name", "proxy": "Proxy"},
    }
    monkeypatch.setattr(config, "collection_formats", lambda **k: fmts)
    text = "\ufeffsep=;\nName;Set Code;Number;Reg Qty;Foil Qty;Proxy\nA;tst;1;2;1;\nB;tst;2;0;3;\nC;tst;3;4;0;Yes\n"
    read = cs.read_export(text)
    assert read.service == "splitapp"
    got = [(ln["name"], ln["quantity"], ln["finish"]) for ln in read.lines]
    assert got == [("A", 2, "nonfoil"), ("A", 1, "foil"), ("B", 3, "foil")]
    assert read.skipped == {"proxy": 4, "digital": 0}


def test_lines_without_identity_are_kept_for_the_preview_to_report():
    text = "Quantity,Name,Finish,Edition Code,Scryfall ID,Collector Number\n2,Mystery,Normal,,,\n"
    read = cs.read_export(text)
    assert read.lines == [{"quantity": 2, "finish": "nonfoil", "scryfall_id": None, "set": None, "cn": None, "name": "Mystery"}]
    # …while the CLI's read_csv path keeps dropping them, as before.
    assert cs.read_text(text, "archidekt") == []


# ---------- through the one review/apply path ----------

SID = ["00000000-0000-4000-8000-00000000000%d" % i for i in range(1, 5)]

MANABOX = ("Name,Set code,Set name,Collector number,Foil,Rarity,Quantity,ManaBox ID,Scryfall ID,Purchase price,"
           "Misprint,Altered,Condition,Language,Purchase price currency\n"
           f"Card 1,tst,Test,1,normal,rare,5,1,{SID[0]},,false,false,near_mint,en,USD\n"
           f"Card 2,tst,Test,2,etched,rare,1,2,{SID[1]},,false,false,near_mint,en,USD\n"
           f"Card 3,tst,Test,3,normal,rare,2,3,{SID[2]},,false,false,near_mint,en,USD\n")


@pytest.fixture
def owned(tmp_db, seed_cards, make_card, monkeypatch):
    seed_cards([make_card(id=s, oracle_id=f"o{i}", set="tst", collector_number=str(i), name=f"Card {i}") for i, s in enumerate(SID, 1)])
    inventory.inventory_add(SID[0], "nonfoil", 3)
    inventory.inventory_add(SID[3], "nonfoil", 7)      # owned, not in the file: never touched

    def boom(*a, **k):
        raise AssertionError("known printings resolve locally")
    monkeypatch.setattr(scryfall, "resolve_identifiers", boom)


def _qty(sid, finish="nonfoil"):
    with db.connect() as conn:
        r = conn.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?", (sid, finish)).fetchone()
    return r[0] if r else 0


@pytest.fixture
def client(owned, tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    for f in (Path(__file__).resolve().parents[1] / "config").glob("*.toml"):
        shutil.copy(f, tmp_path / f.name)
    (tmp_path / "features.toml").write_text("[features]\ncompanion = false\n")   # files never need the companion
    monkeypatch.delenv("MM_FEATURES", raising=False)
    config._cached_toml.cache_clear()
    from magic_manager.web.app import create_app
    yield TestClient(create_app(serve_frontend=False))
    config._cached_toml.cache_clear()


def test_file_routes_preview_then_apply_one_event(client):
    fmts = client.get("/api/collection/import/formats").json()
    assert {"ManaBox", "Moxfield", "Archidekt"} <= {f["name"] for f in fmts}

    body = {"filename": "cards.csv", "text": MANABOX}
    p = client.post("/api/collection/import/file/preview", json=body)
    assert p.status_code == 200, p.text
    pj = p.json()
    assert (pj["format"], pj["format_name"], pj["label"]) == ("manabox", "ManaBox", "web:file ManaBox · cards.csv")
    rows = {(r["scryfall_id"], r["finish"]): (r["current"], r["incoming"]) for r in pj["rows"]}
    assert rows == {(SID[0], "nonfoil"): (3, 5), (SID[1], "foil"): (0, 1), (SID[2], "nonfoil"): (0, 2)}
    assert pj["not_in_read"] == 1 and _qty(SID[0]) == 3          # preview writes nothing

    a = client.post("/api/collection/import/file/apply", json={**body, "format": "manabox", "mode": "replace"})
    assert a.status_code == 200, a.text
    assert (_qty(SID[0]), _qty(SID[1], "foil"), _qty(SID[2]), _qty(SID[3])) == (5, 1, 2, 7)
    with db.connect() as conn:
        ev = conn.execute("SELECT method, label, mode FROM ingest_events WHERE ingest_id=?", (a.json()["ingest_id"],)).fetchone()
        assert tuple(ev) == ("collection-import", "web:file ManaBox · cards.csv", "replace")
        assert ingest.reconcile_inventory_ledger(conn) == []

    assert client.post("/api/collection/import/file/preview", json=body).json()["already_imported_at"]
    dup = client.post("/api/collection/import/file/apply", json={**body, "mode": "add"})
    assert dup.status_code == 409                                    # the identical read, added again
    assert client.post("/api/collection/import/file/apply", json={**body, "mode": "add", "force": True}).status_code == 200
    assert _qty(SID[0]) == 10


def test_file_routes_refuse_unknown_empty_and_below_pledged(client):
    bad = client.post("/api/collection/import/file/preview", json={"filename": "x.csv", "text": "a,b\n1,2\n"})
    assert bad.status_code == 422 and "ManaBox" in str(bad.json()["detail"])
    empty = client.post("/api/collection/import/file/preview", json={"filename": "x.csv", "text": MANABOX.splitlines()[0] + "\n"})
    assert empty.status_code == 422
    assert client.post("/api/collection/import/file/preview", json={"filename": "x.csv", "text": MANABOX, "format": "nope"}).status_code == 422
    assert client.post("/api/collection/import/file/preview", json={"filename": "x.csv", "text": MANABOX, "cookie": 1}).status_code == 422

    from magic_manager import decks
    d = decks.deck_create("built", "Built")
    with db.connect() as conn:
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                     "VALUES (?, ?, 'nonfoil', 6, '2026-01-01')", (d.deck_id, SID[0]))
        conn.commit()
    r = client.post("/api/collection/import/file/apply", json={"filename": "x.csv", "text": MANABOX, "mode": "replace"})
    assert r.status_code == 409 and r.json()["detail"]["below_pledged"][0]["pledged"] == 6
    assert _qty(SID[0]) == 3 and _qty(SID[2]) == 0                   # all-or-nothing
    assert client.post("/api/collection/import/file/apply", json={"filename": "x.csv", "text": MANABOX, "mode": "replace"},
                       headers={"sec-fetch-site": "cross-site"}).status_code == 403
