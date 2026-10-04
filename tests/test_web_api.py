"""Web chassis + typed API: standard-printing selection, the job runner over SSE,
and the read endpoints. Offline: network seams are monkeypatched."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from magic_manager import edhrec, sets
from magic_manager.api import jobs as jobs_api
from magic_manager.api.edhrec import SyncBulkInput
from magic_manager.web.app import create_app

OID = "bbbbbbbb-0000-0000-0000-000000000001"


def _p(make_card, sid, **kw):
    base = dict(id=sid, oracle_id=OID, name="Sol Ring", type_line="Artifact", collector_number=sid)
    base.update(kw)
    return make_card(**base)


# ---------- sets.standard_printing_by_oracle ----------

def test_standard_printing_prefers_oldest_plain_nonfoil(seed_cards, make_card):
    seed_cards([
        _p(make_card, "s-showcase", set="aaa", released_at="2015-01-01", frame_effects=["showcase"]),
        _p(make_card, "s-borderless", set="bbb", released_at="2014-01-01", border_color="borderless"),
        _p(make_card, "s-foilonly", set="ccc", released_at="2016-01-01", finishes=["foil"]),
        _p(make_card, "s-promo", set="ddd", released_at="2013-01-01", promo=True),
        _p(make_card, "s-arena", set="eee", released_at="2012-01-01", security_stamp="arena"),
        _p(make_card, "s-newplain", set="fff", released_at="2021-01-01"),
        _p(make_card, "s-oldplain", set="ggg", released_at="2019-06-01"),
    ])
    got = sets.standard_printing_by_oracle([OID])
    assert got[OID]["scryfall_id"] == "s-oldplain"
    assert got[OID]["set_code"] == "ggg"


def test_standard_printing_falls_back_to_treated_when_no_standard(seed_cards, make_card):
    seed_cards([
        _p(make_card, "t-new", set="aaa", released_at="2024-01-01", frame_effects=["extendedart"]),
        _p(make_card, "t-old", set="bbb", released_at="2020-01-01", frame_effects=["showcase"]),
    ])
    assert sets.standard_printing_by_oracle([OID])[OID]["scryfall_id"] == "t-old"


def test_unknown_release_date_ranks_after_known(seed_cards, make_card):
    seed_cards([
        _p(make_card, "u-null", set="aaa", released_at=None),
        _p(make_card, "u-dated", set="bbb", released_at="2023-01-01"),
    ])
    assert sets.standard_printing_by_oracle([OID])[OID]["scryfall_id"] == "u-dated"


def test_backfill_released_at_fills_only_nulls(seed_cards, make_card, fake_scryfall):
    seed_cards([
        _p(make_card, "b-null", set="aaa", released_at=None),
        _p(make_card, "b-own", set="aaa", released_at="2001-02-03"),
    ])
    fake_scryfall(all_sets=[{"code": "aaa", "released_at": "1999-09-09"}])
    assert sets.backfill_released_at() == 1
    from magic_manager import db
    with db.connect() as c:
        rows = dict(c.execute("SELECT scryfall_id, released_at FROM cards").fetchall())
    assert rows == {"b-null": "1999-09-09", "b-own": "2001-02-03"}


def test_resync_without_date_keeps_existing_date(seed_cards, make_card):
    seed_cards([_p(make_card, "k", released_at="2010-01-01")])
    seed_cards([_p(make_card, "k", released_at=None)])
    from magic_manager import db
    with db.connect() as c:
        assert c.execute("SELECT released_at FROM cards").fetchone()[0] == "2010-01-01"


# ---------- compare: display printing vs floor price ----------

def test_compare_shows_standard_printing_but_cheapest_price(seed_cards, make_card, fake_scryfall, monkeypatch):
    seed_cards([
        _p(make_card, "cheap-showcase", set="aaa", collector_number="300",
           released_at="2022-01-01", frame_effects=["showcase"], prices={"usd": "0.50"}),
        _p(make_card, "plain", set="bbb", collector_number="7",
           released_at="2010-01-01", prices={"usd": "3.00"}),
    ])
    fake_scryfall(collection_found=[])
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: (ref, {"type_line": "Legendary Creature — X", "oracle_text": ""}))
    page = {"container": {"json_dict": {"cardlists": [{
        "tag": "topcards",
        "cardviews": [{"name": "Sol Ring", "sanitized": "sol-ring",
                       "num_decks": 50, "potential_decks": 100}],
    }]}}}
    monkeypatch.setattr(edhrec, "commander_page", lambda slug: json.loads(json.dumps(page)))

    from magic_manager.api import edhrec as edhrec_api
    out = edhrec_api.compare("Alpha", "Beta")
    card = next(c for c in out.cards if c.name == "Sol Ring")
    assert card.bucket == "both"
    assert card.set_code == "bbb" and card.scryfall_id == "plain"
    assert card.lowest_usd == pytest.approx(0.50)
    assert card.scryfall_url == "https://scryfall.com/card/bbb/7"


# ---------- typed inputs ----------

def test_sync_bulk_input_requires_exactly_one_source():
    with pytest.raises(ValueError):
        SyncBulkInput()
    with pytest.raises(ValueError):
        SyncBulkInput(selector="inventory", families=["fin"])
    assert SyncBulkInput(families=["fin"]).families == ["fin"]


# ---------- job chassis over HTTP + SSE ----------

def _sse_events(client, job_id):
    events, cur = [], {}
    with client.stream("GET", f"/api/jobs/{job_id}/events") as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line.startswith("event:"):
                cur["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                cur["data"] = json.loads(line.split(":", 1)[1].strip())
            elif line.startswith("id:"):
                cur["id"] = int(line.split(":", 1)[1].strip())
            elif line == "" and cur:
                events.append(cur)
                cur = {}
    return events


@pytest.fixture
def client(tmp_db):
    with TestClient(create_app(serve_frontend=False)) as c:
        yield c


def test_sync_bulk_job_streams_progress_and_result(client, monkeypatch):
    monkeypatch.setattr(edhrec, "names_for_bulk", lambda **k: ["A", "B"])

    def fake_sync_bulk(names, *, resume, progress, on_resolve=None):
        for i, n in enumerate(names, 1):
            on_resolve(i, len(names), n)
        for i, n in enumerate(names, 1):
            progress(i, len(names), n, "card-only")
        return edhrec.BulkSyncResult(total=len(names), ok=len(names), card_only=len(names))

    monkeypatch.setattr(edhrec, "sync_bulk", fake_sync_bulk)

    r = client.post("/api/jobs/edhrec.sync_bulk", json={"families": ["fin"]})
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]

    events = _sse_events(client, job_id)
    types = [e["event"] for e in events]
    assert types[0] == "status" and types[-1] == "status"
    assert events[-1]["data"]["status"] == "succeeded"
    progress = [e["data"] for e in events if e["event"] == "progress"]
    assert [p["done"] for p in progress] == [0, 1, 2, 1, 2]
    assert progress[1]["message"] == "Checking A…"
    assert progress[-1]["message"] == "B — card-only"
    result = next(e for e in events if e["event"] == "result")["data"]
    assert result["artifacts"][0]["data"]["ok"] == 2
    assert [e["id"] for e in events] == sorted(e["id"] for e in events)

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "succeeded" and "2 synced" in job["summary"]


def test_failed_job_reports_error(client, monkeypatch):
    def boom(**k):
        raise RuntimeError("kaput")
    monkeypatch.setattr(edhrec, "names_for_bulk", boom)
    job_id = client.post("/api/jobs/edhrec.sync_bulk", json={"selector": "inventory"}).json()["id"]
    events = _sse_events(client, job_id)
    assert events[-1]["data"]["status"] == "failed"
    assert any(e["event"] == "error" and "kaput" in e["data"]["error"] for e in events)


def test_job_validation_and_unknown(client):
    assert client.post("/api/jobs/edhrec.sync_bulk", json={}).status_code == 422
    assert client.post("/api/jobs/nope", json={}).status_code == 404
    specs = client.get("/api/jobs/specs").json()
    spec = next(s for s in specs if s["name"] == "edhrec.sync_bulk")
    assert "families" in spec["input_schema"]["properties"]


def test_late_subscriber_replays_history(client, monkeypatch):
    monkeypatch.setattr(edhrec, "names_for_bulk", lambda **k: ["A"])
    monkeypatch.setattr(edhrec, "sync_bulk",
                        lambda names, *, resume, progress, on_resolve=None: edhrec.BulkSyncResult(total=1, ok=1))
    job_id = client.post("/api/jobs/edhrec.sync_bulk", json={"families": ["x"]}).json()["id"]
    first = _sse_events(client, job_id)
    again = _sse_events(client, job_id)   # job already terminal → full replay, then close
    assert [e["id"] for e in first] == [e["id"] for e in again]


def test_job_registry_rejects_duplicates():
    spec = jobs_api.get("edhrec.sync_bulk")
    with pytest.raises(ValueError):
        jobs_api.register(spec)


# ---------- read endpoints ----------

def test_compare_endpoint_maps_engine_errors(client, monkeypatch):
    def bad(a, b):
        raise edhrec.EdhrecError("not commander-eligible")
    monkeypatch.setattr(edhrec, "compare_commanders", bad)
    r = client.get("/api/edhrec/compare", params={"a": "x", "b": "y"})
    assert r.status_code == 422 and "commander" in r.json()["detail"]


def test_commander_search_filters_eligibility(client, seed_cards, make_card):
    seed_cards([
        make_card(id="c1", collector_number="1", oracle_id="o1", name="Tifa Lockhart", type_line="Legendary Creature — Human Monk"),
        make_card(id="c2", collector_number="2", oracle_id="o2", name="Tifa's Limit Break", type_line="Instant"),
        make_card(id="c3", collector_number="3", oracle_id="o3", name="Lockhart Legend", type_line="Legendary Artifact"),
    ])
    names = [o["name"] for o in client.get("/api/edhrec/commanders", params={"q": "tifa"}).json()]
    assert names == ["Tifa Lockhart"]


def test_openapi_schema_exposes_contracts(client):
    schema = client.get("/openapi.json").json()
    comps = schema["components"]["schemas"]
    for name in ("CompareOut", "CollectionOut", "CommanderOption", "JobOut"):
        assert name in comps
