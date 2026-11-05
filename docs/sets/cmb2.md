# `cmb2` — Mystery Booster Playtest Cards 2021

> Per-family memory doc. Read this before answering set-specific questions about
> `cmb2` or working on `cmb2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cmb2`
**Family root type:** `funny`
**Family released:** 2021-08-20
**Last audit:** 2026-11-04 via `/characterize-set cmb2` (one-at-a-time run — tier decisions pending owner review).

---

> **Playtest cards.** 121 R&D "playtest" joke/prototype cards (the
> `playtest` promo type on every print), one per pack of the 2021 Mystery
> Booster Convention Edition (MTGJSON `mb1` booster `convention-2021`, sheet
> `playtest2`). Not tournament-legal. A reprint of [`cmb1`](cmb1.md) (2019):
> the same 121 cards at the same CNs, but its own family.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cmb2` | funny | 121 | 2021-08-20 | parent — the only set, CN 1–121 |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| playtest base (nonfoil-only) | 121 | `cmb2` 1–121 (black border; 8 `legendary`) | `regular` | rarity/base sub-selectors — Scryfall rates **every card `rare`**, so all 121 reach `rare-regular` |

**`promo_types` signals:** `playtest` on all 121 — a set-wide marker, not a
dupe or stamp. Nothing to dedup → proposed `[dupe_foil] cmb2 = []` only to
enable `mm query missing-set cmb2`.

No security stamps, no full-art, no foils.

---

## 3. Chase variants

None. One printing per card.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cmb2 = []` | 0 | **apply** — empty, enables missing-set |
| whole set | 121 | keep or don't track — owner's call whether playtest cards are a completion target |

**Totals (local prices, 2026-11-04):** ≈ $66 nonfoil for all 121; Slivdrazi
Monstrosity 102 (~$14) and Planequake 59 (~$5.75) lead, most are under $1.

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Uniform `rare` rarity** — a rarity filter can't separate "good" playtest
  cards from filler; use `value>=` instead.
- `set_type: funny` — included in master-list set types, so the cards appear
  in checklists and Collection.
- Nonfoil only.
- **Same cards as `cmb1`** at the same CNs; 119 of 121 share art (Soulmates 84
  and Yawgmoth's Testament 52 differ). The 2019 `cmb1` prints are worth
  several times more (Slivdrazi Monstrosity ~$55 vs ~$14).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.cmb2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cmb2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Mystery Booster Convention Edition (2021) | booster product (`mb1`) | one `cmb2` card per pack — MTGJSON `mb1` booster `convention-2021`, sheet `playtest2` |

**Booster types (for `sealed-value` EV):** none — `scripts/sealed_value.py cmb2
--list-boosters` → "no booster data in MTGJSON".
