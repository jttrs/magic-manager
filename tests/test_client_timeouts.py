"""Phase 5: no hang path — every wrapper client passes a timeout and maps a
timeout to its own error class (via ``util.run_wrapper``)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from magic_manager import (
    commander_spellbook, ebay, edhrec, manapool, mtgjson, scryfall, tcgapi, tcgcsv, util,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "magic_manager"

# (module, error class, service label, representative call, expected timeout)
CASES = [
    ("scryfall", scryfall, scryfall.ScryfallError, "Scryfall", lambda: scryfall.named("Island"), util.WRAPPER_TIMEOUT),
    ("scryfall-bulk", scryfall, scryfall.ScryfallError, "Scryfall", lambda: scryfall.bulk_file("oracle_tags"), util.WRAPPER_BULK_TIMEOUT),
    ("mtgjson", mtgjson, mtgjson.MtgJsonError, "MTGJSON", lambda: mtgjson._run(["meta"]), util.WRAPPER_TIMEOUT),
    ("mtgjson-bulk", mtgjson, mtgjson.MtgJsonError, "MTGJSON", lambda: mtgjson._run(["set", "FIN"]), util.WRAPPER_BULK_TIMEOUT),
    ("edhrec", edhrec, edhrec.EdhrecError, "EDHREC", lambda: edhrec.commander_page("atraxa"), util.WRAPPER_TIMEOUT),
    ("spellbook", commander_spellbook, commander_spellbook.CommanderSpellbookError, "Commander Spellbook",
     lambda: commander_spellbook._run(["variants", "x"]), util.WRAPPER_TIMEOUT),
    ("manapool", manapool, manapool.ManapoolError, "Mana Pool", lambda: manapool._run(["products", "x"]), util.WRAPPER_TIMEOUT),
    ("tcgcsv", tcgcsv, tcgcsv.TcgcsvError, "TCGcsv", lambda: tcgcsv._run(["raw", "/x"]), util.WRAPPER_TIMEOUT),
    ("tcgapi", tcgapi, tcgapi.TcgapiError, "TCGAPI", lambda: tcgapi._run(["raw", "/x"]), util.WRAPPER_TIMEOUT),
    ("tcgapi-probe", tcgapi, tcgapi.TcgapiError, "TCGAPI", lambda: tcgapi.TcgapiMarketProvider(), util.WRAPPER_TIMEOUT),
    ("ebay", ebay, ebay.EbayError, "eBay", lambda: ebay._run(["raw", "/x"]), util.WRAPPER_TIMEOUT),
    ("ebay-probe", ebay, ebay.EbayError, "eBay", lambda: ebay.EbayAdvisoryProvider(), util.WRAPPER_TIMEOUT),
]
IDS = [c[0] for c in CASES]


@pytest.fixture(autouse=True)
def _wrappers_exist(monkeypatch):
    for m in (scryfall, mtgjson, edhrec, commander_spellbook, manapool, tcgcsv, tcgapi, ebay):
        monkeypatch.setattr(m, "WRAPPER", Path(__file__))  # exists; never executed


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_timeout_maps_to_client_error(monkeypatch, case):
    _, _, err, service, call, expected = case

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    monkeypatch.setattr(util.subprocess, "run", boom)
    with pytest.raises(err, match=rf"{re.escape(service)} didn't answer in time \({expected} s\)"):
        call()


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_call_site_passes_expected_timeout(monkeypatch, case):
    _, _, err, _, call, expected = case
    seen = {}

    def fake(argv, **kw):
        seen.update(kw)
        raise subprocess.TimeoutExpired(argv, kw["timeout"])

    monkeypatch.setattr(util.subprocess, "run", fake)
    with pytest.raises(err):
        call()
    assert seen["timeout"] == expected


def test_constants():
    assert util.WRAPPER_TIMEOUT == 120 and util.WRAPPER_BULK_TIMEOUT == 1800


def test_mtgjson_bulk_commands():
    assert mtgjson._BULK_COMMANDS == {"set", "decklist", "refresh"}


def test_no_wrapper_subprocess_without_timeout():
    """Source scan: a module that locates a ``.claude/skills`` wrapper must not
    call ``subprocess.run/Popen/check_output`` directly unless that call passes
    ``timeout=`` (the normal path is ``util.run_wrapper``, which always does).
    Limits: textual — it matches the call's balanced parentheses, and doesn't
    follow wrappers launched from a module that never names ``.claude``."""
    call = re.compile(r"subprocess\.(?:run|Popen|check_output|check_call)\(")
    bad = []
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        if '".claude"' not in text and "'.claude'" not in text:
            continue
        for m in call.finditer(text):
            depth, i = 1, m.end()
            while depth and i < len(text):
                depth += {"(": 1, ")": -1}.get(text[i], 0)
                i += 1
            if "timeout=" not in text[m.end():i]:
                bad.append(f"{path.name}:{text.count(chr(10), 0, m.start()) + 1}")
    assert not bad, f"wrapper subprocess call without timeout=: {bad}"
