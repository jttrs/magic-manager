# `mh1` — Modern Horizons

> Per-family memory doc. Read this before answering set-specific questions about
> `mh1` or working on `mh1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mh1`
**Family root type:** `draft_innovation`
**Family released:** 2019-06-14
**Last audit:** 2026-11-05 via `/characterize-set mh1` (one-at-a-time run — tier decisions pending owner review).

---

> **A straight-to-Modern draft set with almost no alt treatments.** No showcase,
> extended-art or borderless prints, and no Collector Booster. The only alt
> prints are full-art snow basics, the buy-a-box Flusterstorm and two promos.
> The retro-frame reprints of MH1 cards ("MH1 Timeshifts", `h1r`) belong to
> [`mh2`](mh2.md), not this family.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mh1` | draft_innovation | 255 | 2019-06-14 | parent — booster set 1–254, buy-a-box 255 |
| `pmh1` | promo | 2 | 2019-06-14 | Morophon `1p` (promo pack, stamped) + Astral Drift `3` (prerelease, datestamped) |
| `amh1` | memorabilia | 54 | 2019-06-14 | Art Series cards (nonfoil, unpriced) |
| `tmh1` | token | 21 | 2019-06-14 | tokens (foil + nonfoil) |

`set:mh1+related` covers all four. Master-list / Collection skip `amh1`
(memorabilia) by default.

---

## 2. Treatments

Survey (`survey_treatment_signature.py MH1`, 608 print-rows by finish).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `mh1` 1–249 (106 C / 80 U / 54 R / 15 M across 1–255) | `regular` | rarity/base sub-selectors — R+M ≈ $442 nonfoil / $1,019 foil (Force of Negation 52 ~$45, The First Sliver 200 ~$37, Ranger-Captain of Eos 21 ~$36, Prismatic Vista 244 ~$29) |
| full-art snow basics | 5 | `mh1` 250–254 (foil + nonfoil) | `fa` | basics — ~$5 nonfoil / ~$36 foil |
| buy-a-box | 1 | `mh1` 255 Flusterstorm (nonfoil-only) | `regular` | rare-regular. A reprint (first printed `cmd` 46) with its own MH1 art |
| promo pack | 1 | `pmh1` `1p` Morophon, the Boundless | `regular` | dupe of base + stamp (~$8 / ~$13) |
| prerelease | 1 | `pmh1` `3` Astral Drift (foil) | `regular` | auto-dropped |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 1 print, auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** | 1 print; ONE/NEO/TDM `stamped` rule |
| `buyabox` | — | distinct art | kept |

No fancy-foil sheet → proposed `[dupe_foil] mh1 = []` to enable `mm query missing-set mh1`.

**Full-art convention:** the snow basics 250–254 only.

---

## 3. Chase variants

None among uncommons. The family's chase is in base rares/mythics; the
retro-frame foil reprints live in `h1r` (an [`mh2`](mh2.md) child).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mh1 = []` | 0 | **apply** — empty, enables missing-set |
| `pmh1` `1p` stamped | 1 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$8 |
| buy-a-box 255 | 1 | keep — distinct art |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `1p` | `pmh1` | Promo Pack, stamped | Morophon, the Boundless |
| `3` | `pmh1` | prerelease, datestamped (foil) | Astral Drift |
| `255` | `mh1` | Buy-a-Box | Flusterstorm |

---

## 7. Edge cases & gotchas

- **Mostly new cards:** only 25 of 254 booster prints reprint a card that
  existed before 2019-06-14 (by the local catalog, which undercounts — see
  [`c19`](c19.md) §7).
- **`h1r` points at `mh2`, not `mh1`.** `set:mh1+related` won't include the MH1
  Timeshifts; use `set:mh2+related` or `set:h1r`.
- **Only two promos** — MH1 had no full Promo Pack / prerelease run like a
  standard-legal set.
- Flusterstorm 255 is nonfoil-only.
- **The coverage audit reports `borderless×54`**: that is the `amh1` Art
  Series (memorabilia, borderless, off by default), not a card treatment.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mh1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mh1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | no Collector Booster, no Bundle |
| Art Series | memorabilia | `amh1` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mh1 --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$11.41, 100% coverage |
