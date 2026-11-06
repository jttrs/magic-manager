# `soi` — Shadows over Innistrad

> Per-family memory doc. Read this before answering set-specific questions about
> `soi` or working on `soi`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `soi`
**Family root type:** `expansion`
**Family released:** 2016-04-08
**Last audit:** 2026-11-05 via `/characterize-set soi` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion with transforming DFCs** (`sunmoondfc`). Intro Packs
> instead of Planeswalker Decks. Its promo set has alt-art Intro Pack foils, a
> Gift Box card, a buy-a-box card, and an inverted Game Day Anguished Unmaking
> (~$32). Sibling: [`emn`](emn.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `soi` | expansion | 297 local (Scryfall set metadata says 302) | 2016-04-08 | parent — booster set 1–297 (basics 283–297) |
| `psoi` | promo | 90 | 2016-04-08 | prerelease `Ns` datestamped (77) + Promo Pack `Np` stamped (2) + Intro Pack foils (5) + game day / release / buy-a-box / Gift Box (6) |
| `tsoi` | token | 20 | 2016-04-08 | tokens |

`set:soi+related` covers all three. The [`w16`](w16.md) Welcome Decks were
given out alongside SOI.

---

## 2. Treatments

Survey (`survey_treatment_signature.py SOI`): every print computes `regular`
except the inverted Game Day Anguished Unmaking (`b`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 297 | `soi` 1–297 (120 C / 100 U / 59 R / 18 M; 33 transforming DFCs) | `regular` | rarity/base sub-selectors — R+M ≈ $87 nonfoil / $197 foil (Relentless Dead 131 ~$12, Cryptolith Rite 200 ~$12, Eerie Interlude 16 ~$6, Sorin, Grim Nemesis 251) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 77 prints, auto-dropped (~$431 foil) |
| `promopack` + `stamped` | `regular` | **yes** — `psoi` `Np` = base + stamp | 2 prints (Anguished Unmaking `242p`, Eerie Interlude `16p`), ~$16 / $44 |
| `intropack` | — | **no** — own art | 5 foil rares (Drogskol Cavalry 15, Nephalia Moondrakes 75, Markov Dreadknight 122, Flameblade Angel 157, Soul Swallower 230) |
| `gameday` | — | **no** — own art | Anguished Unmaking 242 (inverted, `b`, ~$32), Incorrigible Youths 166 |
| `release` + `datestamped` | — | **no** — own art | Angel of Deliverance 2 |
| `buyabox` | — | **no** — own art | Elusive Tormentor 108 |
| `giftbox` | — | **no** — own art | Ravenous Bloodseeker 175 (SOI Gift Box) |

No fancy-foil sheet → proposed `[dupe_foil] soi = []` to enable `mm query missing-set soi`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons. The pricey alt is the Game Day Anguished Unmaking 242.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] soi = []` | 0 | **apply** — empty, enables missing-set |
| `psoi` promo-pack stamped `Np` | 2 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$16 |
| `psoi` Intro Pack foils | 5 | **owner's call** — own art, came in a retail product |
| `psoi` game day / release / buy-a-box / Gift Box | 6 | **owner's call** — all have their own art; Anguished Unmaking 242 is ~$32 |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `psoi` | prerelease, datestamped (foil) | — |
| `Np` | `psoi` | Promo Pack, stamped | Anguished Unmaking `242p` |
| `15`, `75`, `122`, `157`, `230` | `psoi` | Intro Pack foil (alt art) | Flameblade Angel 157 |
| `166`, `242` | `psoi` | Game Day (alt art) | Anguished Unmaking 242 |
| `2` | `psoi` | Release (alt art, datestamped) | Angel of Deliverance |
| `108` | `psoi` | Buy-a-Box (alt art) | Elusive Tormentor |
| `175` | `psoi` | Gift Box (alt art) | Ravenous Bloodseeker |

---

## 7. Edge cases & gotchas

- **Tamiyo's Journal 265 is nonfoil-only** in Scryfall — the only booster rare
  with no foil print.
- **Local count is 297 of Scryfall's 302** for `soi`.
- Angel of Deliverance 2 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.soi.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.soi]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | Angelic Fury, Ghostly Tide, Horrific Visions, Unearthed Secrets, Vampiric Thirst; each with a foil `psoi` rare |
| Gift Box | gift bundle | `psoi` 175 + Gift Box Land Pack (pool) |
| Fat Pack / Deck Builder's Toolkit | Bundle / kit | Fat Pack Land Pack (pool); toolkit decklists in MTGJSON |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py soi --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$2.78, 92.3% coverage |
| `prerelease` | ~$4.52 |
