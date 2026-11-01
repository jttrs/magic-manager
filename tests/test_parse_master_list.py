"""parse_master_list_xlsx (entries/warnings/meta) and the shared
read_master_list_rows reader it is built on."""

from __future__ import annotations

from openpyxl import Workbook

from magic_manager import parsers


def _book(tmp_path, header, rows, *, sheet="checklist", meta=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for r in rows:
        ws.append(r)
    if meta is not None:
        ms = wb.create_sheet("_meta")
        ms.append(["key", "value"])
        for k, v in meta.items():
            ms.append([k, v])
    path = tmp_path / "x.xlsx"
    wb.save(path)
    return path


HEADER = ["Set", "collector_number", "name", "qty_normal", "qty_foil"]


def test_parse_entries_warnings_and_meta_unchanged(tmp_path):
    path = _book(tmp_path, HEADER, [
        ["TST", 1, "Alpha", 2, 1],
        ["tst", 2, "Beta", None, 0],        # blank / zero -> no entry, no warning
        [None, None, None, None, None],     # fully empty row skipped
        ["tst", 3, "Gamma", "x", -1],       # bad + negative -> warnings, treated as 0
    ], meta={"anchor_code": "tst", "kind": "inventory"})
    res = parsers.parse_master_list_xlsx(path)
    assert [(e.set, e.collector_number, e.name, e.qty, e.foil, e.raw) for e in res.entries] == [
        ("tst", "1", "Alpha", 2, False, "row 2: 2 Alpha (tst) 1"),
        ("tst", "1", "Alpha", 1, True, "row 2: 1 Alpha (tst) 1 ★"),
    ]
    assert res.warnings == [
        "row 5: 'qty_normal' value 'x' is not an integer; treating as 0",
        "row 5: 'qty_foil' value -1 is negative; treating as 0",
    ]
    assert res.meta == {"anchor_code": "tst", "kind": "inventory"}


def test_parse_missing_columns_warns(tmp_path):
    path = _book(tmp_path, ["set", "name"], [["tst", "Alpha"]])
    res = parsers.parse_master_list_xlsx(path)
    assert res.entries == [] and res.meta is None
    assert res.warnings == [
        "XLSX missing required columns: ['collector_number', 'qty_normal', 'qty_foil']"]


def test_read_rows_keeps_blank_and_zero_rows_and_falls_back_to_first_sheet(tmp_path):
    path = _book(tmp_path, HEADER, [["tst", 1, "Alpha", None, 0], [None, None, None, None, None]],
                 sheet="Sheet1")
    sheet = parsers.read_master_list_rows(path)
    assert sheet.meta is None and sheet.missing_columns == [] and sheet.warnings == []
    assert [(r.row_num, r.set, r.collector_number, r.qty_normal_raw, r.qty_foil_raw)
            for r in sheet.rows] == [(2, "tst", "1", None, 0)]
