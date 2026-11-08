# `cmb1` — Mystery Booster Playtest Cards 2019

> Per-family memory doc. Read this before answering set-specific questions about
> `cmb1` or working on `cmb1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cmb1`
**Family root type:** `funny`
**Family released:** 2019-11-07
**Last audit:** 2026-11-05 via `/characterize-set cmb1` (one-at-a-time run — tier decisions pending owner review).

---

> **Playtest cards from the 2019 Mystery Booster Convention Edition.** 121 R&D
> prototype/joke cards (`playtest` promo type on every print), one per
> Convention Edition pack (MTGJSON `mb1` booster `convention`, sheet
> `playtest`). Not tournament-legal. The 2021 Convention Edition reprinted all
> 121 as [`cmb2`](cmb2.md) — same names, same CNs, almost all the same art (§7).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cmb1` | funny | 121 | 2019-11-07 | parent — the only set, CN 1–121 |

No children. Related but separate: `mb1` (the Mystery Booster itself),
`cmb2` (the 2021 reprint run).

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| playtest cards (nonfoil-only) | 121 | `cmb1` 1–121 (black border; 8 `legendary`) | `regular` | Scryfall rates **every card `rare`**, so all 121 reach `rare-regular` |

**`promo_types` signals:** `playtest` on all 121 — a set-wide marker, not a
dupe or stamp. Configured `[dupe_foil] cmb1 = []` (2026-11-08) only to enable
`mm query missing-set cmb1`.

No foils, no full-art, no stamps.

---

## 3. Chase variants

None within the set. The 2019 prints sell well above their 2021 `cmb2`
reprints: Slivdrazi Monstrosity 102 ~$55 (vs ~$14), Sliv-Mizzet 99 ~$19
(vs ~$2.50), Soulmates 84 ~$18 (vs ~$0.80), Planequake 59 ~$17 (vs ~$6).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cmb1 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole set | 121 | **owner's call** whether playtest cards are a completion target (≈ $243 nonfoil for all 121) |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **`cmb1` and `cmb2` are the same 121 cards.** Every `cmb1` oracle reappears in
  `cmb2` at the same collector number; 119 of 121 share the illustration (only
  Soulmates 84 and Yawgmoth's Testament 52 got new art). Identify a physical
  copy by its edition, not its art: the 2019 print is the pricier one.
  Owning one doesn't complete the other in missing-set.
- **Uniform `rare` rarity**: filter by `value>=`, not rarity.
- MTGJSON lists 125 uuids for the set vs Scryfall's 121 cards.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cmb1 = []` — configured 2026-11-08 (enables `mm query missing-set cmb1`).
- `config/families.toml` `[[unobtainable.cmb1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cmb1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Mystery Booster Convention Edition (2019) | booster product (`mb1`) | one `cmb1` card per pack — MTGJSON `mb1` booster `convention`, sheet `playtest` (all 121, equal weight) |

**Booster types (for `sealed-value` EV):** none for `cmb1` itself. Value the
pack as `sealed_value.py mb1` booster `convention` (EV ~$16).
