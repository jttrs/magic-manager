"""Scryfall art tags + printing→illustration link (V30): migration, projection,
backfill, kind-isolated sync, and the printings_with_art engine query.

Fixtures under ``fixtures/scryfall_art/`` are RECORDED excerpts (2026-10-04):
``art_tags_sample.jsonl`` — 10 real art tags (dragon ⊃ east-asian dragon, cat, …)
with taggings trimmed to three illustrations; ``cards_sample.jsonl`` — the three
real ``default_cards`` lines carrying those illustration_ids. ``scryfall.bulk_file``
is monkeypatched, so no wrapper/HTTP is touched.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from magic_manager import db, inventory, scryfall, scryfall_art, scryfall_tags

FIX = Path(__file__).parent / "fixtures"
ART_FIXTURE = FIX / "scryfall_art" / "art_tags_sample.jsonl"
CARDS_FIXTURE = FIX / "scryfall_art" / "cards_sample.jsonl"
ORACLE_FIXTURE = FIX / "scryfall_tags" / "oracle_tags_sample.jsonl"

DRAGON = "4d00f045-fb84-4e11-a3c0-d736f947c67e"
EA_DRAGON = "adfe7a92-023d-4b55-8368-ea9a3fc645f8"
CAT = "504aea75-b144-4530-b014-3e3c7a1fd283"
SCORCH, SCORCH_ORACLE, SCORCH_ILL = ("05c4338d-e5c0-46b4-ab16-1f9aa97b4026",
                                     "6f9bce77-f7f0-453b-86cd-1e6bd71980a3",
                                     "03cbf046-fb37-487b-9f3f-d833dea540fa")
ZODIAC, ZODIAC_ORACLE, ZODIAC_ILL = ("46652ae3-6572-4296-939b-0789923180d5",
                                     "e5c2cf0f-c1c0-4fd6-9b5f-7d4aa25246a7",
                                     "d294cbf1-9e23-4f68-a43b-20bbdcdbb2a4")
BLUFFS, BLUFFS_ORACLE = "6ba13d72-be1b-4421-be62-62c2b35defe8", "b66deeb5-7371-4f06-b10e-d65165bc07b2"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _gz(path: Path, rows: list[dict]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows))
    return path


@pytest.fixture
def bulks(tmp_path, monkeypatch):
    files = {
        "art_tags": _gz(tmp_path / "art_tags--art-tags-20261004090119.jsonl.gz", _jsonl(ART_FIXTURE)),
        "oracle_tags": _gz(tmp_path / "oracle_tags--oracle-tags-20261004090034.jsonl.gz", _jsonl(ORACLE_FIXTURE)),
        "default_cards": _gz(tmp_path / "default_cards--default-cards-20261004090531.jsonl.gz",
                             _jsonl(CARDS_FIXTURE)),
    }
    monkeypatch.setattr(scryfall, "bulk_file", lambda t, *, refresh=False: files[t])
    return files


def _seed_printings(seed_cards, make_card):
    """Local printings WITHOUT illustration ids (as in a pre-V30 DB)."""
    seed_cards([
        make_card(id=SCORCH, oracle_id=SCORCH_ORACLE, name="Scorch the Fields", set="dka", collector_number="103"),
        make_card(id=ZODIAC, oracle_id=ZODIAC_ORACLE, name="Zodiac Dragon", set="ptk", collector_number="131"),
        make_card(id=BLUFFS, oracle_id=BLUFFS_ORACLE, name="Painted Bluffs", set="plst", collector_number="AKH-246"),
        make_card(id="tok-1", oracle_id="tok-o", name="Dragon Token", set="ttst", collector_number="1",
                  layout="token"),
    ])


@pytest.fixture
def art_db(tmp_db, bulks, seed_cards, make_card):
    _seed_printings(seed_cards, make_card)
    scryfall_tags.sync(kind="art")
    scryfall_art.backfill_illustration_ids()
    return tmp_db


# ---------- V30 + projection ----------

def test_v30_columns_and_tables(tmp_db):
    with db.connect() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(cards)")}
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "illustration_id" in cols and "illustration_art_tags" in tables
    assert {"cards_illustration_idx", "illustration_art_tags_tag_idx"} <= idx
    assert db.CURRENT_VERSION == 32


def test_upsert_projects_illustration_and_never_nulls(tmp_db, make_card):
    top = make_card(id="a", illustration_id="ill-top")
    faces = make_card(id="b", collector_number="2", layout="transform", card_faces=[
        {"name": "F", "illustration_id": "ill-front"}, {"name": "B", "illustration_id": "ill-back"}])
    with db.connect() as conn:
        db.upsert_cards(conn, [top, faces])
        got = dict(conn.execute("SELECT scryfall_id, illustration_id FROM cards"))
        assert got == {"a": "ill-top", "b": "ill-front"}
        # re-sync without the field must keep the stored value
        db.upsert_card(conn, make_card(id="a"))
        assert conn.execute("SELECT illustration_id FROM cards WHERE scryfall_id='a'").fetchone()[0] == "ill-top"


# ---------- backfill ----------

def test_backfill_fills_only_nulls(tmp_db, bulks, seed_cards, make_card):
    _seed_printings(seed_cards, make_card)
    with db.connect() as conn:  # one row already has a (different) value
        conn.execute("UPDATE cards SET illustration_id = 'keep-me' WHERE scryfall_id = ?", (BLUFFS,))
    assert scryfall_art.backfill_illustration_ids() == 2
    with db.connect() as conn:
        got = dict(conn.execute("SELECT scryfall_id, illustration_id FROM cards"))
    assert got[SCORCH] == SCORCH_ILL and got[ZODIAC] == ZODIAC_ILL
    assert got[BLUFFS] == "keep-me" and got["tok-1"] is None
    assert scryfall_art.backfill_illustration_ids() == 0  # idempotent


# ---------- kind-isolated sync ----------

def test_art_and_oracle_sync_are_isolated(tmp_db, bulks):
    scryfall_tags.sync(kind="oracle")
    o_before = scryfall_tags.status(kind="oracle")
    res = scryfall_tags.sync(kind="art")
    assert (res.tags, res.taggings) == (10, 3)
    assert scryfall_tags.status(kind="oracle") == o_before  # art sync left oracle alone
    a_before = scryfall_tags.status(kind="art")
    scryfall_tags.sync(kind="oracle", refresh=True)
    assert scryfall_tags.status(kind="art") == a_before     # and vice versa
    assert scryfall_tags.sync(kind="art").skipped


def test_function_roots_and_hierarchy_never_see_art_tags(tmp_db, bulks):
    scryfall_tags.sync_kinds()
    ids = {i for r in scryfall_tags.function_roots() for i in r.tag_ids}
    assert ids and not ids & {DRAGON, EA_DRAGON, CAT}
    assert scryfall_tags.descendants(DRAGON) == set()                       # oracle hierarchy: unknown
    assert scryfall_tags.descendants(DRAGON, kind="art") == {EA_DRAGON}


# ---------- engine query ----------

def test_tag_lookup_by_label_slug_uuid(art_db):
    for ref in ("east-asian dragon", "EAST-ASIAN-DRAGON", EA_DRAGON):
        assert scryfall_art.resolve_tag(ref) == (EA_DRAGON, "east-asian dragon")
    assert scryfall_art.resolve_tag("nope") is None
    with pytest.raises(LookupError):
        scryfall_art.printings_with_art("nope")


def test_art_tag_search(art_db):
    hits = scryfall_art.art_tag_search("dragon")
    assert [h["slug"] for h in hits] == ["dragon", "east-asian-dragon"]  # exact first
    assert hits[0]["illustrations"] == 1 and set(hits[0]) == {"id", "label", "slug", "illustrations"}
    assert scryfall_art.art_tag_search("dragon", limit=1) == hits[:1]


def test_printings_with_art_rollup_filters_and_owned(art_db):
    rows = scryfall_art.printings_with_art("dragon")
    assert [r["scryfall_id"] for r in rows] == [SCORCH, ZODIAC]   # roll-up includes child's art
    z = rows[1]
    assert z["tags"] == ["east-asian dragon"] and z["weight"] == "very_strong"
    assert z["illustration_id"] == ZODIAC_ILL and z["owned"] == 0
    assert {"scryfall_id", "oracle_id", "name", "set_code", "collector_number"} <= set(z)
    # no roll-up → only the directly tagged illustration
    assert [r["scryfall_id"] for r in scryfall_art.printings_with_art("dragon", include_descendants=False)] == [SCORCH]
    # restricted to given oracle ids
    only = scryfall_art.printings_with_art("dragon", oracle_ids=[ZODIAC_ORACLE])
    assert [r["scryfall_id"] for r in only] == [ZODIAC]
    assert scryfall_art.printings_with_art("dragon", oracle_ids=[]) == []
    # owned only
    assert scryfall_art.printings_with_art("dragon", owned_only=True) == []
    inventory.inventory_add(ZODIAC, "nonfoil", 2)
    owned = scryfall_art.printings_with_art("dragon", owned_only=True)
    assert [(r["scryfall_id"], r["owned"]) for r in owned] == [(ZODIAC, 2)]
    assert [r["scryfall_id"] for r in scryfall_art.printings_with_art("cat")] == [BLUFFS]


def test_digital_only_and_tokens_excluded(art_db, make_card):
    with db.connect() as conn:
        conn.execute("UPDATE cards SET promo_types = '[\"alchemy\"]' WHERE scryfall_id = ?", (SCORCH,))
        conn.execute("UPDATE cards SET illustration_id = ?, is_token = 1 WHERE scryfall_id = 'tok-1'",
                     (ZODIAC_ILL,))
    assert [r["scryfall_id"] for r in scryfall_art.printings_with_art("dragon")] == [ZODIAC]


def test_art_tags_for_printings(art_db):
    got = scryfall_art.art_tags_for_printings([SCORCH, ZODIAC, BLUFFS, "tok-1", "missing"])
    assert got == {SCORCH: ["dragon"], ZODIAC: ["east-asian dragon"], BLUFFS: ["cat"]}


# ---------- CLI ----------

def test_cli_art_smoke(art_db):
    from typer.testing import CliRunner
    from magic_manager.cli import app

    inventory.inventory_add(ZODIAC, "nonfoil", 1)
    r = CliRunner().invoke(app, ["scryfall", "art", "dragon"])
    assert r.exit_code == 0, r.output
    assert "2 printing(s)" in r.output and "Zodiac Dragon" in r.output
    r = CliRunner().invoke(app, ["scryfall", "art", "dragon", "--owned"])
    assert "1 printing(s)" in r.output and "Scorch" not in r.output
    r = CliRunner().invoke(app, ["scryfall", "art", "dragon", "--cards", "Scorch the Fields"])
    assert "1 printing(s)" in r.output and "Scorch the Fields" in r.output
    r = CliRunner().invoke(app, ["scryfall", "art", "nope"])
    assert r.exit_code == 1


def test_cli_tags_sync_kind_and_backfill(tmp_db, bulks, seed_cards, make_card):
    from typer.testing import CliRunner
    from magic_manager.cli import app

    _seed_printings(seed_cards, make_card)
    r = CliRunner().invoke(app, ["scryfall", "tags", "sync", "--kind", "art"])
    assert r.exit_code == 0 and "art tags synced: 10 tags" in r.output and "oracle" not in r.output
    r = CliRunner().invoke(app, ["scryfall", "tags", "sync"])
    assert "oracle tags synced" in r.output and "art tags already current" in r.output
    r = CliRunner().invoke(app, ["set", "backfill-illustrations"])
    assert r.exit_code == 0 and "filled illustration_id on 3 card rows" in r.output
