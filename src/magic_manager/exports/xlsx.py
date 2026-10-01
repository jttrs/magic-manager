"""Shared XLSX workbook writer — ONE home for the openpyxl boilerplate that had
been hand-rolled in ~7 places (cli._write_query_xlsx + the _write_xlsx in
construct_value / edhrec_report / jumpstart_buildable / jumpstart_reference /
review_earmarks / sealed_value).

A caller declares each sheet as a :class:`SheetSpec` (headers + pre-materialized
cell rows + a few per-column hints) and calls :func:`write_workbook`; the writer
owns the shared conventions every artifact shares:

- bold, left-aligned header row;
- per-column widths;
- per-column number formats — ``money_cols`` → ``"$"#,##0.00``; ``text_cols`` →
  ``@`` (forces CNs / product ids to text, dodging Excel's "number stored as
  text" nag);
- per-column hyperlinks via a ``(row, row_index) → url|None`` callable (e.g. a
  Scryfall link on the name cell — the index lets a caller align with a
  precomputed URL list when the URL isn't itself a cell value), styled
  blue+underline like a web link;
- ``freeze`` panes (default ``A2``);
- a hidden ``_meta`` sheet when ``meta`` is given;
- ``util.apply_base_font_size`` on EVERY sheet, then ``mkdir -p`` + save.

Cells are plain values the caller computed — this module adds no domain logic,
only presentation, so it stays a thin dependency of both the package and the
standalone scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .. import util

# Blue + single underline — matches the inventory/master-list hyperlink styling.
_LINK_COLOR = "0563C1"
_MONEY_FMT = '"$"#,##0.00'
_TEXT_FMT = "@"


@dataclass
class SheetSpec:
    """One worksheet: a title, a header row, and already-materialized cell rows,
    plus optional per-column presentation hints (all column indices 1-based)."""
    title: str
    headers: Sequence[str]
    rows: Iterable[Sequence]
    widths: dict[int, int] = field(default_factory=dict)
    money_cols: Sequence[int] = ()           # format as "$"#,##0.00
    text_cols: Sequence[int] = ()            # format as @ (text) — CNs, product ids
    hyperlinks: dict[int, Callable[[Sequence, int], str | None]] = field(default_factory=dict)
    freeze: str | None = "A2"
    hidden: bool = False


def meta_sheet(pairs: Sequence[tuple[str, str]], *, title: str = "_meta") -> SheetSpec:
    """A hidden two-column ``key``/``value`` sheet — the convention
    cli._write_query_xlsx and the checklist writers use to stamp a file with its
    originating selector / kind / timestamp."""
    return SheetSpec(
        title=title, headers=["key", "value"],
        rows=[[k, v] for k, v in pairs], hidden=True, freeze=None,
    )


def write_workbook(path: Path, sheets: Sequence[SheetSpec]) -> None:
    """Write ``sheets`` to an XLSX at ``path`` (parents created). The first spec
    becomes the active sheet; the rest are appended in order."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    link_font = Font(color=_LINK_COLOR, underline="single")

    for i, spec in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = spec.title
        if spec.hidden:
            ws.sheet_state = "hidden"

        ws.append(list(spec.headers))
        for col in range(1, len(spec.headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="left")

        money = set(spec.money_cols)
        text = set(spec.text_cols)
        for data_idx, row_vals in enumerate(spec.rows):
            ws.append(list(row_vals))
            ridx = ws.max_row
            for col in money:
                ws.cell(row=ridx, column=col).number_format = _MONEY_FMT
            for col in text:
                ws.cell(row=ridx, column=col).number_format = _TEXT_FMT
            for col, url_of in spec.hyperlinks.items():
                uri = url_of(row_vals, data_idx)
                if uri:
                    c = ws.cell(row=ridx, column=col)
                    c.hyperlink = uri
                    c.font = link_font

        for col, w in spec.widths.items():
            ws.column_dimensions[get_column_letter(col)].width = w
        if spec.freeze:
            ws.freeze_panes = spec.freeze

    for ws in wb.worksheets:
        util.apply_base_font_size(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
