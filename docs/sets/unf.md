# `unf` — `Unfinity`

> Per-family memory doc. Read this before answering set-specific questions about
> `unf` or working on `unf`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `unf`
**Family root type:** `funny` (Un-set; mix of acorn-stamped non-tournament cards and oval-stamped eternal-legal cards)
**Family released:** 2022-10-07
**Last audit:** 2026-11-02 via `/characterize-set unf` (batch run; tier decisions pending owner review).

---

## 1. Family map

Resolved via `mm set list-related unf`; all three codes synced locally (701 prints).

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `unf` | funny | 639 | 2022-10-07 | parent; base 1–234 (135 lettered CNs), alt/boosterfun 235–286, galaxy foil 287–537, `release` promo 538 |
| `sunf` | funny | 48 | 2022-10-07 | Sticker Sheets (CN 1–48, nonfoil only; 1 per Draft Booster, `sunfSticker` slot) |
| `tunf` | token | 14 | 2022-10-07 | tokens (tracked, never in missing-set); CN 14 Ticket Bucket-Bot nonfoil-only |

**Separately-rooted, NOT in this family:** `ulst` — *The List (Unfinity Foil Edition)*, 62 cards, `parent_set_code: plst`, released the same day. It is the Collector Booster's `foilUn-list` slot (foil reprints of older Un-cards), but Scryfall roots it under The List, so `set:unf+related` does not include it. It is synced locally. Add it explicitly only if the owner wants it tracked with Unfinity:

```
mm set master-list unf --only unf,sunf,tunf,ulst
```

Checked Scryfall `/sets` 2022-09-15 → 2022-11-30: no other Unfinity-linked set (`punf` does not exist — no prerelease/promo-pack set).

---

## 2. Treatments

All boosterfun prints carry `promo_types: boosterfun`; the galaxy-foil sheet adds `galaxyfoil`. Structure from `survey_treatment_signature.py UNF` (TREATMENT-FIRST AXIS) + local DB:

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 335 | 1–234 (200 numeric + 135 lettered CNs) | `regular` | rarity / chase sub-selectors |
| Attraction lit-number variants | 134 | 200a–234b | `regular` | same illustration, different lit numbers (functionally distinct) — 2 (rare) / 4 / 6 (C/U) per name; surface as `chase` (§3) |
| showcase, black border (legendary "poster" frame) | 29 | 245–274 | `shw` | **kept (default) — pending owner review.** Distinct art from base (e.g. Katerina 16 → 245). ~$0.10–0.55 each |
| showcase + inverted, black border | 1 | 270 (The Space Family Goblinson) | `b\|shw` | **kept (default) — pending owner review** (same showcase tier, extra `inverted` effect) |
| borderless "planet" basics (full art) | 10 | 235–244 (two arts per basic type) | `b` | **kept (default) — pending owner review.** Only basics in the set; $0.66–3.96 |
| borderless shocklands (inverted) | 10 | 277–286 | `b` | **kept (default) — pending owner review.** Reprint shocks, $19–31 nonfoil; also the Box Topper (traditional foil) |
| borderless alt-art mythics (no frame effect) | 2 | 275 Comet, Stellar Pup / 276 Space Beleren | `regular` (!) | ⚠ compute to `regular` (borderless without `inverted`/full_art) → surface via the mythic-regular sub-selector, not `preferred`. Distinct art from 166 / 178 |
| galaxy foil (same art as a non-galaxy print) | 251 | 287–537 | `ff` (201), `shw\|ff` (30), `b\|ff` (10), `fa\|ff` (10) | dupe foils — **all 251 share `illustration_id` with a non-galaxy `unf` print** (verified). Dropped once `[dupe_foil] unf = ["galaxyfoil"]` is configured (every one computes with `ff`) |
| `release` promo | 1 | 538 Water Gun Balloon Game (foil only) | `regular` | only printing of the card; rare-regular sub-selector |
| extended-art / etched | 0 | — | — | none present |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `galaxyfoil` | `ff` | **yes** → proposed `[dupe_foil] unf = ["galaxyfoil"]` | 251 prints, Collector-Booster-only galaxy-foil sheet. Includes the scarcity tier of galaxy shocks 528–537 ($100–182 each, ~$1,320 total) and galaxy basics 486–495 — all same art as 235–244 / 277–286 |
| `boosterfun` | — | umbrella | skipped by axis 1; real structure is in `frame_effects` |
| `release` | — | no sibling | 538 only |

**Full-art convention:** inconsistent on Scryfall. `full_art = TRUE` on borderless basics 235–244, galaxy basics 486–495, and 8 of the 10 borderless shocks (277, 280–286) — but FALSE on 278 Watery Grave / 279 Blood Crypt and on all galaxy shocks 528–537. Treatment is unaffected (`b`/`b|ff` either way) because the shocks are `inverted` + borderless.

**Galaxy basics frame quirk:** 486–490 are **black-bordered** full-art galaxy basics sharing the illustration of borderless 235–239; 491–495 are borderless and share 240–244. Same art, so still dupe foils.

---

## 3. Chase variants

Only **Attractions** trigger `chase` — their lettered CN variants differ in lit-up numbers, not art (except Scavenger Hunt and The Superlatorium, which have 6 distinct illustrations each). The modifier counts printings, so same-art attraction variants qualify.

`set:unf+related missing rarity=uncommon treatment=regular chase` (58 rows, nonfoil + foil):

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Balloon Stand / Bounce Chamber / Concession Stand / Guess Your Fate / Information Booth / Roller Coaster / Trash Bin | 4 each | 200a–d, 201a–d, 205a–d, 215a–d, 218a–d, 225a–d, 232a–d | uncommon | regular |
| Bumper Cars / Squirrel Stack / Trivia Contest | 6 each | 202a–f, 228a–f, 233a–f | uncommon | regular |
| Scavenger Hunt / The Superlatorium | 6 each (**6 distinct arts**) | 226a–f, 230a–f | uncommon | regular |

Common attractions with 4–6 variants (Clown Extruder, Costume Shop, Cover the Spot, Dart Throw, Drop Tower, Foam Weapons Kiosk, Fortune Teller, Kiddie Coaster, Pick-a-Beeble, Spinny Ride) also match bare `chase`. Rare attractions have only 2 variants (a/b) → below the threshold. `chase:5` keeps only the six-variant names (30 rows).

---

## 4. Scenes / posters / panoramas

None detected. The inverted borderless prints (basics 235–244, shocks 277–286) are per-card treatments by different artists, not contiguous same-artist panoramas. No `poster` promo_type.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Candidate | Status | Rationale |
|---|---|---|
| galaxy foil sheet (287–537) | proposed **dupe-foil**, not an unobtainable rule | same art as non-galaxy prints; all compute with `ff`, so `[dupe_foil] unf = ["galaxyfoil"]` drops them (incl. the ~$1,320 galaxy-shock scarcity tier) |
| black-bordered showcase legends (245–274, 30) | kept (default) — pending owner review | distinct art, cheap; the set's only showcase frame |
| borderless planet basics (235–244) | kept (default) — pending owner review | only basics in the set |
| borderless shocklands (277–286) | kept (default) — pending owner review | ~$260 nonfoil for the 10; the family's highest-value kept tier |
| Attraction lit-number variants (134 lettered CNs) | kept (default) — pending owner review | same art, functionally distinct; a "one per attraction" preference would need a `collector_numbers` rule |

Before/after missing totals: n/a (family unconfigured; `set_status.py` can't compute missing until `[dupe_foil]` exists). Rough local-price shape: galaxy foils $1,760 total (dropped by the dupe-foil proposal); everything else in `unf`+`sunf` ≈ $411 at nonfoil-else-foil prices, led by the ten borderless shocks.

Filtered globally: no serialized, no digital/arena prints (`missing | grep -i arena` → 0).

---

## 6. PRM destinations

n/a — Unfinity has no prerelease/promo-pack set (`punf` doesn't exist). The only promo is `unf` 538 Water Gun Balloon Game (`promo_types: release`, foil only), filed in the parent set.

---

## 7. Edge cases & gotchas

- **Lettered CNs.** 135 `unf` CNs carry a letter suffix: Attractions 200a–234b (2/4/6 variants) and `107m` "Name Sticker" Goblin. Use the exact CN (`200c`) for `add-cards`/bulk-add.
- **Comet, Stellar Pup / Space Beleren borderless (275/276) compute `regular`.** They're distinct-art alt prints but bypass the treatment sub-selector; they appear as mythic-regular rows.
- **Acorn vs oval stamp.** `security_stamp: acorn` = not tournament legal; `oval` = eternal-legal (shocks, basics, some commons/legends). Legality is per-card, not per-band.
- **Shocklands are reprints** (also in many other sets); the `unf` borderless versions are the distinct art here. Traditional-foil borderless shocks are also the Box Topper (`box-topper` sheet `foilShockland`).
- **`sunf` stickers** are a separate funny set, nonfoil only; one sticker sheet per Draft Booster.
- **`ulst`** (The List, Unfinity Foil Edition) is a Collector Booster slot but rooted under `plst` — see §1.
- Comet, Stellar Pup is also reprinted in `mb2` 79 (white border) — not part of this family.

---

## 8. Code refs

None configured yet (proposals pending owner review).

- `config/families.toml` `[dupe_foil]` — no `unf` entry (proposal: `unf = ["galaxyfoil"]`).
- `config/families.toml` `[[unobtainable.unf.rules]]` — none.
- Scenes — none.

---

## 9. Product types

No precons, no Bundle, no Jumpstart. MTGJSON sealed products: Draft Booster Pack / Box (36 + 1 Box Topper) / Case, Collector Booster Pack / Box (12 + 1 Box Topper) / Case, Box Topper Pack, 3-Booster Draft Pack.

| Product | Archetype (→ [product-types.md](../product-types.md)) | Family-specific detail |
|---|---|---|
| Unfinity Draft Booster Box | booster box | 36 Draft Boosters + 1 Box Topper Pack |
| Unfinity Collector Booster Box | booster box | 12 Collector Boosters + 1 Box Topper Pack |
| Unfinity Box Topper Pack | booster pack (topper) | 1 traditional-foil borderless shockland (277–286) |

**Booster types (for `sealed-value` EV)** — `sealed_value.py unf --list-boosters`:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | 2 attractions + 1 sticker sheet (`sunf`) + C/U/R slots with showcase mixed in; basic slot is the planet basics, rarely a borderless shock (`shock` slot, 3/72 weight). EV $5.57, 99.9% coverage |
| `collector` | all foil: traditional foil + galaxy foil sheets (galaxy shock in ~4% of packs (weight 96/2304)), plus 1 `foilUn-list` slot pointing at `ulst` (separately rooted — keep `ulst` synced for coverage). EV $21.27, 99.7% coverage |
| `box-topper` | 1 foil borderless shockland. EV $29.04, 100% coverage |
