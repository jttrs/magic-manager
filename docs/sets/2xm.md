# `2xm` — Double Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `2xm` or working on `2xm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `2xm`
**Family root type:** `masters`
**Family released:** 2020-08-07
**Last audit:** 2026-11-04 via `/characterize-set 2xm` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `2xm` | masters | 384 | 2020-08-07 | parent — main set 1–332, box toppers 333–372, basics 373–382, buy-a-box 383–384 |
| `t2xm` | token | 31 | 2020-08-07 | tokens (17 full-art) |

No promo set, no prerelease (masters). `set:2xm+related` covers the family.
Sibling: [`2x2`](2x2.md) (Double Masters 2022).

---

## 2. Treatments

Survey (`survey_treatment_signature.py 2XM`, 415 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| main set | 332 | `2xm` 1–332 (91 C / 80 U / 121 R / 40 M) | `regular` | rarity/base sub-selectors — R+M ≈ $1,617 nonfoil (Mox Opal 275 ~$222, Chrome Mox 240 ~$165) |
| **box toppers — borderless, no `inverted`** | 2 | `2xm` 333 Karn Liberated, 334 Jace, the Mind Sculptor (`boxtopper`, `boosterfun`) | `regular` (borderless without `inverted` → no `b`, as in [`cmr`](cmr.md) 512–513) | **kept (default) — pending owner review.** mythic-regular lists them beside base. **334 Jace reuses the base art of `2xm` 56** — a true same-art alt |
| **box toppers — borderless `inverted`** | 38 | `2xm` 335–372 (`boxtopper`, `boosterfun`; rare + mythic) | `b` | **kept (default) — pending owner review.** Each is a borderless reprint of a main-set card (40/40 share an `oracle_id` with 1–332), new art. One per Draft-booster box / VIP pack. ~$1,971 nonfoil / ~$2,218 foil total for 333–372 (Mox Opal 362 ~$381, Force of Will 340 ~$206, Chrome Mox 358 ~$185) |
| full-art basics | 10 | `2xm` 373–382 (`boosterfun`, two of each) | `regular` | basics, never rare/mythic |
| buy-a-box | 2 | `2xm` 383 Wrath of God, 384 Chord of Calling (`release`+`buyabox`, foil) | `regular` | rare-regular |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boxtopper` + `boosterfun` | `b` / `regular` | same CARD as a main-set print, different art (except Jace 334) | 40 prints; the family's alt-$ |
| `release` + `buyabox` | — | distinct | 383–384 |

No fancy-foil sheet → configured `[dupe_foil] 2xm = []` (2026-11-08) to enable `mm query missing-set 2xm`.

**Full-art convention:** `full_art = 1` on 17 `t2xm` tokens (basics 373–382 are full-art frame but flagged via promo, not `full_art`).

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 2xm = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| box toppers 333–372 | 40 | **owner's call** — ~$1,971 nonfoil, more than the whole main-set R+M. They're one-per-box chase alts of cards already in 1–332; keep if completing the box-topper sheet is a goal, else exclude with `cn_range = [333, 372]` |
| Jace 334 (same art as 56) | 1 | if the toppers are kept, this one is still a same-art borderless dupe — candidate for exclusion on its own |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `333`–`372` | `2xm` | Box topper (1 per Draft box, VIP Edition pack) | Mox Opal 362 |
| `383`–`384` | `2xm` | Buy-a-Box (foil) | Wrath of God |

---

## 7. Edge cases & gotchas

- **Everything is foil + nonfoil** (Draft boosters had two foils per pack);
  box toppers too.
- **Box-topper borderless frames compute differently**: 333–334 have no
  `inverted` frame effect → `regular`; 335–372 → `b`.
- Mox Opal and Chrome Mox appear twice each (base + topper) — the topper is
  ~1.7× the base.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] 2xm = []` — configured 2026-11-08 (enables `mm query missing-set 2xm`).
- `config/families.toml` `[[unobtainable.2xm.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.2xm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters (box with 1 box topper) | booster product | 2 rares + 2 foils per pack |
| VIP Edition | premium booster | 2 box toppers + foils |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 2xm --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$23.90, 100% coverage |
| `box-topper` | EV ~$83.06 |
| `vip` | EV ~$141.19 |
