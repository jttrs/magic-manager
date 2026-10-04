"""Scryfall Tagger oracle tags (V28): migration, offline sync, roll-up, compare
enrichment, CLI relay + job spec.

The fixture ``fixtures/scryfall_tags/oracle_tags_sample.jsonl`` is a RECORDED
excerpt of Scryfall's real ``oracle_tags`` bulk file (2026-10-04): 12 real tags
(real UUIDs + hierarchy) with taggings trimmed to three cards — Sol Ring, Wrath
of God, Swords to Plowshares. ``scryfall.bulk_file`` is monkeypatched to return
a gzip copy of it, so no wrapper/HTTP is touched.
"""
from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pytest

from magic_manager import config, db, scryfall, scryfall_tags

FIXTURE = Path(__file__).parent / "fixtures" / "scryfall_tags" / "oracle_tags_sample.jsonl"

SOL_RING = "6ad8011d-3471-4369-9d68-b264cc027487"
WRATH = "34515b16-c9a4-4f98-8c77-416a7a523407"
SWORDS = "b1544f21-7e98-461b-aed5-e748b0168c52"
RAMP = "2f3e4ad7-5e60-41b4-bdbc-653f16869cf6"
MANA_ROCK = "523a4f29-25ee-483c-8123-a8e62b62af5a"
MANA_PRODUCER = "5f1260dd-e1dc-435a-a9ff-ce7172b7a5cd"


@pytest.fixture
def bulk(tmp_path, monkeypatch):
    """Serve the fixture as the daily bulk file; returns a setter to swap files."""
    calls = {"n": 0, "refresh": []}
    state = {}

    def _write(name: str, rows: list[dict] | None = None) -> Path:
        p = tmp_path / f"oracle_tags--oracle-tags-{name}.jsonl.gz"
        with gzip.open(p, "wt", encoding="utf-8") as f:
            if rows is None:
                shutil.copyfileobj(open(FIXTURE, encoding="utf-8"), f)
            else:
                f.write("\n".join(json.dumps(r) for r in rows))
        state["path"] = p
        return p

    def fake_bulk_file(bulk_type, *, refresh=False):
        assert bulk_type == "oracle_tags"
        calls["n"] += 1
        calls["refresh"].append(refresh)
        return state["path"]

    monkeypatch.setattr(scryfall, "bulk_file", fake_bulk_file)
    _write("20261004090034")
    return {"write": _write, "calls": calls}


def _fixture_rows() -> list[dict]:
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


# ---------- V28 ----------

def test_v28_tables_exist(tmp_db):
    with db.connect() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        v = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert {"scryfall_tags", "card_oracle_tags"} <= tables
    assert "card_oracle_tags_tag_idx" in idx
    assert v == db.CURRENT_VERSION == 28


# ---------- sync ----------

def test_sync_ingests_fixture_and_is_idempotent(tmp_db, bulk):
    res = scryfall_tags.sync()
    assert (res.tags, res.taggings, res.skipped) == (12, 9, False)
    assert res.updated_at == "2026-10-04T09:00:34+00:00"
    # Same daily file again → skipped, nothing rewritten.
    again = scryfall_tags.sync()
    assert again.skipped and (again.tags, again.taggings) == (12, 9)
    # refresh forces a rewrite (same counts — full re-derive, no dupes).
    forced = scryfall_tags.sync(refresh=True)
    assert not forced.skipped and (forced.tags, forced.taggings) == (12, 9)
    assert bulk["calls"]["refresh"] == [False, False, True]
    with db.connect() as conn:
        parents = json.loads(conn.execute(
            "SELECT parent_ids FROM scryfall_tags WHERE id = ?", (MANA_ROCK,)).fetchone()[0])
    assert MANA_PRODUCER in parents  # mana-rock ⊂ mana-producer ⊂ ramp


def test_new_daily_file_replaces_stale_taggings(tmp_db, bulk):
    scryfall_tags.sync()
    rows = _fixture_rows()
    for t in rows:  # upstream untagged Sol Ring from mana-rock
        if t["id"] == MANA_ROCK:
            t["taggings"] = []
    bulk["write"]("20261005090000", rows)
    res = scryfall_tags.sync()
    assert not res.skipped and res.taggings == 8
    assert "ramp" not in scryfall_tags.roll_up([SOL_RING]).get(SOL_RING, [])


def test_load_bulk_accepts_json_array(tmp_path):
    p = tmp_path / "tags.json"
    p.write_text(json.dumps(_fixture_rows()))
    assert len(scryfall_tags.load_bulk(p)) == 12


# ---------- hierarchy + roll-up ----------

def test_descendants_and_roll_up_through_hierarchy(tmp_db, bulk):
    scryfall_tags.sync()
    assert {MANA_PRODUCER, MANA_ROCK} <= scryfall_tags.descendants(RAMP)
    assert RAMP not in scryfall_tags.descendants(RAMP)
    up = scryfall_tags.roll_up([SOL_RING, WRATH, SWORDS, "no-such-oracle"])
    # Sol Ring is tagged only `mana-rock` (+ meta) → rolls up to Ramp.
    assert up[SOL_RING] == ["ramp"]
    # Wrath is a `sweeper` (child of removal) → Removal AND Board wipe, config order.
    assert up[WRATH] == ["removal", "board-wipe"]
    assert up[SWORDS] == ["removal", "lifegain"]
    assert "no-such-oracle" not in up


def test_function_root_falls_back_to_slug_when_uuid_renamed(tmp_db, bulk, monkeypatch):
    scryfall_tags.sync()
    cfg = config.function_tags()
    cfg = {**cfg, "roots": [{"key": "ramp", "label": "Ramp",
                             "tags": [{"id": "stale-uuid", "slug": "ramp"}]}]}
    monkeypatch.setattr(config, "function_tags", lambda **k: cfg)
    roots = scryfall_tags.function_roots()
    assert roots[0].key == "ramp" and MANA_ROCK in roots[0].tag_ids


def test_card_summaries_rank_and_exclude_meta(tmp_db, bulk):
    scryfall_tags.sync()
    summ = scryfall_tags.card_summaries([SOL_RING, WRATH])
    sol = [t.slug for t in summ[SOL_RING].tags]
    assert sol[0] == "mana-rock"                    # very_strong first
    assert "activated-ability" not in sol            # preview_exclude subtree
    wrath = [t.slug for t in summ[WRATH].tags]
    assert wrath[0] == "sweeper"
    # functional tag outranks a same-weight non-functional one
    assert wrath.index("removal-creature") < wrath.index("symmetrical")
    assert summ[WRATH].functions == ["removal", "board-wipe"]


def test_lookups_empty_before_sync(tmp_db):
    assert scryfall_tags.card_summaries([SOL_RING]) == {}
    assert scryfall_tags.roll_up([SOL_RING]) == {}
    assert scryfall_tags.status()["source"] is None


# ---------- config ----------

def test_function_tags_toml_matches_baked_default(tmp_path):
    from_file = config.function_tags()
    baked = config.function_tags(override=tmp_path)  # empty dir → defaults
    assert from_file == baked
    keys = [r["key"] for r in baked["roots"]]
    assert keys == ["ramp", "draw", "removal", "board-wipe", "counterspell", "tutor",
                    "recursion", "protection", "token-maker", "sac-outlet",
                    "lifegain", "evasion"]


# ---------- compare enrichment (one batched lookup) ----------

def test_compare_commanders_carries_functions_and_tags(tmp_db, bulk, fake_scryfall,
                                                       seed_cards, make_card, monkeypatch):
    from magic_manager import edhrec
    from test_edhrec import _cardview, _page

    scryfall_tags.sync()
    seed_cards([
        make_card(id="00000000-0000-0000-0000-0000000000a1", oracle_id=SOL_RING,
                  name="Sol Ring", type_line="Artifact"),
        make_card(id="00000000-0000-0000-0000-0000000000a2", oracle_id=WRATH,
                  name="Wrath of God", type_line="Sorcery", collector_number="2"),
    ])
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: (ref, {"type_line": "Legendary Creature — Elf", "oracle_text": ""}))
    fake_scryfall(collection_found=[])
    pages = {
        "alpha": _page({"topcards": [_cardview("Sol Ring", "sol-ring", num_decks=9, potential_decks=10)]}),
        "beta": _page({"topcards": [_cardview("Wrath of God", "wrath-of-god", num_decks=5, potential_decks=10)]}),
    }
    monkeypatch.setattr(edhrec, "commander_page", lambda slug: dict(pages[slug]))
    calls = {"n": 0}
    real = scryfall_tags.card_summaries

    def counting(oids, **k):
        calls["n"] += 1
        return real(oids, **k)

    monkeypatch.setattr(scryfall_tags, "card_summaries", counting)
    res = edhrec.compare_commanders("Alpha", "Beta")
    by = {c.name: c for c in res.cards}
    assert calls["n"] == 1
    assert by["Sol Ring"].functions == ["ramp"]
    assert by["Wrath of God"].functions == ["removal", "board-wipe"]
    assert by["Sol Ring"].oracle_tags[0] == {"id": MANA_ROCK, "slug": "mana-rock", "label": "mana rock"}

    from magic_manager.api import edhrec as edhrec_api
    out = edhrec_api.compare("Alpha", "Beta")
    assert [f.key for f in out.functions][:3] == ["ramp", "draw", "removal"]
    sol = next(c for c in out.cards if c.name == "Sol Ring")
    assert sol.functions == ["ramp"] and sol.oracle_tags[0].slug == "mana-rock"


# ---------- CLI + job ----------

def test_cli_tags_sync_and_show(tmp_db, bulk, seed_cards, make_card):
    from typer.testing import CliRunner
    from magic_manager.cli import app

    seed_cards([make_card(oracle_id=SOL_RING, name="Sol Ring")])
    r = CliRunner().invoke(app, ["scryfall", "tags", "sync"])
    assert r.exit_code == 0, r.output
    assert "12 tags" in r.output
    r = CliRunner().invoke(app, ["scryfall", "tags", "show", "Sol Ring"])
    assert r.exit_code == 0, r.output
    assert "functions: ramp" in r.output


def test_sync_tags_job_spec(tmp_db, bulk):
    from magic_manager.api import jobs

    spec = jobs.get("scryfall.sync_tags")
    events = []
    res = spec.run(spec.input_model(), events.append)
    assert "12 tags" in res.summary and events
    assert res.artifacts[0].data["taggings"] == 9


def test_preview_keeps_functional_tag_even_under_meta_root(tmp_db, monkeypatch):
    rows = [
        {"id": "fn", "slug": "fn", "label": "fn", "child_ids": ["x"], "taggings": []},
        {"id": "meta", "slug": "meta", "label": "meta", "child_ids": ["x", "y"], "taggings": []},
        {"id": "x", "slug": "x", "label": "x", "parent_ids": ["fn", "meta"],
         "taggings": [{"oracle_id": "o1", "weight": "median"}]},
        {"id": "y", "slug": "y", "label": "y", "parent_ids": ["meta"],
         "taggings": [{"oracle_id": "o1", "weight": "median"}]},
    ]
    scryfall_tags.ingest(rows, source="t", updated_at=None)
    cfg = {"roots": [{"key": "f", "label": "F", "tags": [{"id": "fn", "slug": "fn"}]}],
           "preview_limit": 5, "preview_exclude": ["meta"]}
    monkeypatch.setattr(config, "function_tags", lambda **k: cfg)
    summ = scryfall_tags.card_summaries(["o1"])["o1"]
    assert summ.functions == ["f"]
    assert [t.slug for t in summ.tags] == ["x"]
