# `phuk` — Hachette UK

> Per-family memory doc. Read this before answering set-specific questions about
> `phuk` or working on `phuk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `phuk`
**Family root type:** `box`
**Family released:** 2006-01-01
**Last audit:** 2026-11-06 via `/characterize-set phuk` (one-at-a-time run — tier decisions pending owner review).

---

> **A 60-card mono-black Rats deck from a Hachette UK partwork (magazine series), all Kamigawa-era rat cards plus Swamps. Standalone root, no children, no prices.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `phuk` | box | 60 | 2006-01-01 | parent — 36 spells + 24 Swamps, interleaved CNs 1–60 |

The anchor is always included by `mm set master-list phuk`, whatever its
`set_type`.

---

## 2. Treatments

All `regular`; every print is nonfoil and `promo_types = ["mediainsert"]` (2 also `tombstone`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck cards | 36 | `phuk` 1–7, 13–19, 25–31, 37–44, 49–55 (Marrow-Gnawer 1, Patron of the Nezumi 25, Larceny 49, Diabolic Tutor 51, Betrayal of Flesh 52; many cards appear 2–3× under different CNs) | `regular` | rarity sub-selectors (5 R / 13 U / 18 C) — **unpriced** |
| Swamps | 24 | `phuk` 8–12, 20–24, 32–36, 45–48, 56–60 | `regular` | basics |

**New art (local check):** none certain — the art comes from Kamigawa-block and older printings, some of which aren't synced locally. Proposed `[dupe_foil] phuk = []` to enable
`mm query missing-set phuk`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] phuk = []` —
**apply**. Whole family (60) — **owner's call**: a UK magazine-partwork deck; kept (default) — pending owner review.

---

## 7. Edge cases & gotchas

- **Repeated cards are separate printings:** Carrion Rats is CN 40, 41 and 53; Swarm of Rats 2, 14, 27, etc. A distinct-printing count overstates distinct cards.
- **No prices** on Scryfall — value/missing-$ figures read $0.
- Not in MTGJSON's deck list or sealed products.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.phuk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.phuk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Hachette partwork deck | magazine insert (`mediainsert`) | one 60-card deck |

**Booster types (for `sealed-value` EV):** none.
