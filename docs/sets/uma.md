# `uma` — Ultimate Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `uma` or working on `uma`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `uma`
**Family root type:** `masters`
**Family released:** 2018-12-07
**Last audit:** 2026-11-05 via `/characterize-set uma` (one-at-a-time run — tier decisions pending owner review).

---

> **An all-reprint Masters set with a box-topper sheet.** 254 reprints in base
> frame plus 40 extended-art foil box toppers (`puma` U1–U40) that **reuse the
> `uma` art** of the same card. No promos, no showcase/borderless.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `uma` | masters | 254 | 2018-12-07 | parent — CN 1–254, every print foil + nonfoil |
| `puma` | masterpiece | 40 | 2018-12-07 | Ultimate Box Topper — CN `U1`–`U40`, extended-art, foil-only, mythic |
| `tuma` | token | 16 | 2018-12-07 | tokens (nonfoil) |

`set:uma+related` covers all three. `masterpiece` is a default inventory set
type, so master-list / Collection include `puma`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py UMA`, 564 print-rows by finish).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base reprints (foil + nonfoil) | 254 | `uma` 1–254 (101 C / 80 U / 53 R / 20 M) | `regular` | rarity/base sub-selectors — R+M ≈ $962 nonfoil / $1,344 foil (Ancient Tomb 236 ~$126, Mana Vault 229 ~$114, Demonic Tutor 93 ~$66) |
| **box toppers** | 40 | `puma` U1–U40 (`boxtopper`, `extendedart`, foil-only, all mythic) | `ext` | **auto-dropped** by the preferred filter (ext class). Each is the same CARD **and the same art** as its `uma` print (40/40 share `illustration_id`), in an extended frame. ~$1,885 foil (Mana Vault U29 ~$266, Ancient Tomb U31 ~$212, Urborg U40 ~$189, Cavern of Souls U32 ~$170) |
| tokens | 16 | `tuma` 1–16 | `regular` | tokens |

**`promo_types` dupe-foil / stamped signals:** only `boxtopper` (40). No promo
child, no prerelease / promo-pack prints. Configured `[dupe_foil] uma = []` (2026-11-08) to
enable `mm query missing-set uma`.

**Full-art convention:** none.

---

## 3. Chase variants

The `puma` box toppers (above) — one per Draft Booster box.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] uma = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `puma` box toppers | 40 | already dropped by the ext preferred class; nothing to add. If you want them listed, that's an explicit keep (owner's call). Same question as [`2xm`](2xm.md)'s toppers, but here the art is the same as base |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `U1`–`U40` | `puma` | Box Topper (one per Draft Booster box) | Mana Vault U29 |

---

## 7. Edge cases & gotchas

- **Box-topper CNs carry a `U` prefix** and sort as 0 under a numeric cast —
  use the string CN.
- **Same art as base, unlike later toppers.** [`2xm`](2xm.md)'s and
  [`iko`](iko.md)'s toppers have new art; UMA's are the `uma` illustration in an
  extended frame. A "same art" check flags all 40.
- **Toppers compute `ext`, not `b`,** so they're dropped by default — the
  opposite of 2xm's borderless toppers (kept by default).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] uma = []` — configured 2026-11-08 (enables `mm query missing-set uma`).
- `config/families.toml` `[[unobtainable.uma.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.uma]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / box | booster product | each box carries one Box Topper Pack (`puma`) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py uma --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$17.69, 99% coverage |
| `box-topper` | EV ~$47.13, 100% coverage |
