# `rix` — Rivals of Ixalan

> Per-family memory doc. Read this before answering set-specific questions about
> `rix` or working on `rix`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rix`
**Family root type:** `expansion`
**Family released:** 2018-01-19
**Last audit:** 2026-11-05 via `/characterize-set rix` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Ixalan set, base frame only.** Small (196 booster cards), with two
> Planeswalker Decks and the six-card cycle of transforming legendary lands
> (`compasslanddfc`). The Buy-a-Box card is an alternate-art `prix` foil of a
> regular booster rare (Captain's Hook 177).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rix` | expansion | 205 | 2018-01-19 | parent — booster set 1–196 (basics 192–196), PW-deck cards 197–205 |
| `prix` | promo | 98 | 2018-01-19 | prerelease `Ns` datestamped (61) + Promo Pack `Np` stamped (31) + buy-a-box alt art (1) + league / store championship / open house / draft weekend / resale (5) |
| `trix` | token | 7 | 2018-01-19 | tokens |

`set:rix+related` covers all three. The first block set, `xln`, is separately rooted.

---

## 2. Treatments

Survey (`survey_treatment_signature.py RIX`): every print computes `regular`.
`frame_effects` `compasslanddfc` (the transforming-land cycle, 7 prints incl.
one mythic) is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 196 | `rix` 1–196 (75 C / 60 U / 48 R / 13 M) | `regular` | rarity/base sub-selectors — R+M ≈ $132 nonfoil / $286 foil (Polyraptor 144 ~$14, Azor 154 ~$14, The Immortal Sun 180 ~$13, Nezahal 45 ~$10 / $22) |
| transforming legendary lands | 7 | `rix` (Azor's Gateway, Golden Guardian, …; 6 rare + 1 mythic) | `regular` | part of base; `compasslanddfc` is not a treatment |
| Planeswalker-deck exclusives | 9 | `rix` 197 Vraska, Scheming Gorgon + 198–200; 201 Angrath, Minotaur Pirate + 202–205 | `regular` | **unique cards** — keep; walkers foil-only (~$3.45 / ~$5.66), deck mates nonfoil-only |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 61 prints, auto-dropped (~$381 foil total) |
| `promopack` + `stamped` | `regular` | **yes** — `prix` `Np` = base + stamp | 31 prints, ~$149 nonfoil / ~$161 foil; ONE/NEO/TDM `stamped` rule |
| `buyabox` | — | **no** — `prix` 177 Captain's Hook has different art from `rix` 177 (the prerelease `177s` reuses the booster art) | 1 print, foil-only, ~$0.31 |
| `league` / `storechampionship` / `openhouse` / `draftweekend` / `resale` | — | promo-only copies of base cards | 5 prints (Ghalta 130 store championship ~$8) |
| `setpromo` | — | marker on every `prix` print | not a dupe signal |
| `planeswalkerdeck` | — | unique cards | 197–205 |

No fancy-foil sheet → proposed `[dupe_foil] rix = []` to enable `mm query missing-set rix`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] rix = []` | 0 | **apply** — empty, enables missing-set |
| `prix` promo-pack stamped `Np` | 31 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$149 |
| `prix` buy-a-box 177 | 1 | keep — alternate art, ~$0.31 |
| `prix` league / event promos | 5 | **owner's call** — same question as [`war`](war.md) / [`dom`](dom.md) |
| PW-deck 197–205 | 9 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `prix` | prerelease, datestamped (foil) | — |
| `Np` | `prix` | Promo Pack, stamped | — |
| `53` | `prix` | Open House | Silvergill Adept |
| `94` | `prix` | Draft Weekend | Brass's Bounty |
| `100★` | `prix` | resale | Etali, Primal Storm |
| `130` | `prix` | Store Championship | Ghalta, Primal Hunger |
| `177` | `prix` | Buy-a-Box (foil, alternate art) | Captain's Hook |
| `186` | `prix` | League | Evolving Wilds |
| `197`–`205` | `rix` | Planeswalker Decks | Angrath, Minotaur Pirate 201 |

---

## 7. Edge cases & gotchas

- **Buy-a-Box is an alt-art print of a booster card**, unlike `dom`/`m19`/`grn`,
  whose Buy-a-Box cards are unique cards in the parent set. `prix` 177 has its
  own art; `rix` 177 and the prerelease `prix` `177s` share the booster art.
- **Transforming lands** (`compasslanddfc`) have a land back face; selectors
  match on the front name.
- No FNM promos in `prix` (the 6 event promos are other channels).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.rix.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.rix]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Planeswalker Decks ×2 | Planeswalker deck | Vraska / Angrath; cards at 197–205 |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rix --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$4.91, 99.1% coverage |
| `prerelease` / `showdown` | ~$4.78 (88% coverage) / ~$5.56 |
| `arena` | digital code card, ignore |
