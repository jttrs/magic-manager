# `jmp` — `Jumpstart`

> Per-family memory doc. Read this before answering set-specific questions about
> `jmp` or working on `jmp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `jmp`
**Family root type:** `draft_innovation` (standalone Jumpstart product, `parent_set_code: null`)
**Family released:** 2020-07-17
**Last audit:** 2026-11-04 via `/characterize-set jmp` (one-at-a-time run — tier decisions pending owner review).

---

> **The original Jumpstart.** Sold only as 20-card themed packs (46 themes, 121
> pack versions in MTGJSON, all `type: Jumpstart`). Base-frame nonfoil
> throughout; the only alt print is one release-promo foil (CN 496). Track packs
> with `mm set jumpstart-list jmp`, not booster EV. Same shape as
> [`j22`](j22.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `jmp` | draft_innovation | 496 | 2020-07-17 | parent — CN 1–495 pack contents + 496 release promo; 1 `A-` Alchemy rebalance (A-206 Blood Artist) |
| `fjmp` | memorabilia | 46 | 2020-07-17 | Jumpstart Front Cards (theme cards, CN 1–46); ~$2 total |
| `ajmp` | starter (**digital: true**) | 18 | 2020-07-17 | Jumpstart Arena Exclusives — MTG Arena replacements for cards not on Arena; **no paper printing** |

No promo or token child. `set:jmp+related` covers all three; master-list /
Collection skip `fjmp` (memorabilia) by default.

---

## 2. Treatments

Survey (`survey_treatment_signature.py JMP`, 560 prints): all `regular`
nonfoil except CN 496.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (nonfoil-only) | 494 | `jmp` 1–495 (235 C / 156 U / 88 R / 17 M; 39 basics) | `regular` | rarity/base sub-selectors — R+M ≈ $534 (Rhystic Study 169 ~$67, Allosaurus Shepherd 28 ~$50, Bruvac 10 ~$43, Exquisite Blood 231 ~$41) |
| release promo (foil) | 1 | `jmp` 496 Scholar of the Lost Trove (`release`+`datestamped`) | `regular` | rare-regular — same card as base 14 (different art), the only foil in the set |
| front cards | 46 | `fjmp` 1–46 | `regular` | memorabilia — off by default |
| Arena exclusives | 18 | `ajmp` 3–310 | `regular` | **should be digital-only but leak** — see §7 |
| Alchemy rebalance | 1 | `jmp` A-206 | — | dropped by `_is_digital_only` |

`frame_effects` on base prints are cosmetic only (`legendary` 27).

**`promo_types` dupe-foil / stamped signals:** `release`+`datestamped` on 496
only. No fancy-foil sheet → configured `[dupe_foil] jmp = []` (2026-11-08) to enable
`mm query missing-set jmp`.

**Full-art convention:** none.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] jmp = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `ajmp` Arena exclusives | 18 | **exclude** — digital only, unobtainable in paper. Prefer the code fix (§7); until then `[[unobtainable.jmp.rules]]` on set `ajmp` |
| release promo 496 | 1 | keep — distinct art, foil-only |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `496` | `jmp` | release promo (foil, datestamped) | Scholar of the Lost Trove |

---

## 7. Edge cases & gotchas

- **`ajmp` leaks past the digital filter.** The set is `digital: true` on
  Scryfall, yet `uv run mm query show 'set:jmp+related'` returns all 18 `ajmp`
  rows — the same `_is_digital_only` gap seen with `omb` under
  [`mar`](mar.md). Its cards look like normal cards (no `A-` prefix, no arena
  stamp in our columns), so a set-level `digital` check is what's missing.
- **Basics are pack content** — 39 basic-land prints across themes; many share
  oracle ids, so "distinct cards" ≪ prints.
- Scholar of the Lost Trove appears twice (14 base, 496 promo).
- Pack versions: each theme has 1–4 versions (e.g. `Angels (1)`…); see
  `docs/product-types.md` § Jumpstart and `jumpstart.py`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] jmp = []` — configured 2026-11-08 (enables `mm query missing-set jmp`).
- `config/families.toml` `[[unobtainable.jmp.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.jmp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Jumpstart booster (20-card themed pack) | Jumpstart | 46 themes / 121 versions; one random pack per booster |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py jmp --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `jumpstart` | EV ~$10.24, 100% coverage, 121 layouts |
