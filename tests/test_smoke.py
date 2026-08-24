"""Harness smoke test — confirms tmp_db + seed_cards + fakes wire up."""

def test_tmp_db_creates_schema(tmp_db):
    from magic_manager import db
    with db.connect() as conn:
        # cards table exists and is empty in the throwaway DB
        n = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    assert n == 0
    assert str(tmp_db).endswith("test.db")


def test_seed_and_read(seed_cards, make_card):
    from magic_manager import db
    seed_cards([make_card(id="sid-1", set="ncc", collector_number="5", name="Widget")])
    with db.connect() as conn:
        row = conn.execute("SELECT name, set_code FROM cards WHERE scryfall_id='sid-1'").fetchone()
    assert row["name"] == "Widget"
    assert row["set_code"] == "ncc"


def test_fake_scryfall_drives_sync(tmp_db, fake_scryfall, make_card):
    from magic_manager import sets, db
    fake_scryfall(search=[make_card(id="s1", set="ncc"), make_card(id="s2", set="ncc", collector_number="2")])
    n = sets.sync(["ncc"])
    assert n == 2
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2
