# `dom` — Dominaria

> Per-family memory doc. Read this before answering set-specific questions about
> `dom` or working on `dom`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dom`
**Family released:** 2018-04-27
**Family root type:** `expansion`
**Last audit:** 2026-11-05 via `/characterize-set dom` (one-at-a-time run — tier decisions pending owner review).

---

> **Base-frame expansion with two Planeswalker Decks and a Buy-a-Box card.**
> No showcase, extended-art or borderless prints. The first set with the
> Promo Pack `Np` stamped promos that recur through `m19`–`war`. Value sits in
> Mox Amber, Cabal Stronghold and the legendary mythics.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dom` | expansion | 280 | 2018-04-27 | parent — booster set 1–269 (basics 250–269), PW-deck cards 270–279, buy-a-box 280 |
| `pdom` | promo | 117 local (Scryfall set metadata says 118) | 2018-04-27 | prerelease `Ns` datestamped (88) + Promo Pack `Np` stamped (22) + FNM / league / store championship / open house / draft weekend (7) |
| `tdom` | token | 16 | 2018-04-27 | tokens |

`set:dom+related` covers all three.

---

## 2. Treatments

Survey (`survey_treatment_signature.py DOM`): every print computes `regular`
except 3 FNM `inverted` promos (`b`). `frame_effects` `legendary` (the
historic-legendary crown) is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 269 | `dom` 1–269 (121 C / 80 U / 53 R / 15 M; 20 basics 250–269) | `regular` | rarity/base sub-selectors — R+M ≈ $180 nonfoil / $427 foil (Mox Amber 224 ~$85 / $191, Cabal Stronghold 238 ~$14, Teferi, Hero of Dominaria 207 ~$9) |
| Planeswalker-deck exclusives | 10 | `dom` 270 Teferi, Timebender + 271–274; 275 Chandra, Bold Pyromancer + 276–279 | `regular` | **unique cards** — keep; walkers foil-only, deck mates nonfoil-only; ~$5 |
| buy-a-box | 1 | `dom` 280 Firesong and Sunspeaker (foil-only) | `regular` | **unique card** — keep; ~$0.29 |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 88 prints, auto-dropped (Mox Amber `224s` ~$302, Cabal Stronghold `238s` ~$32) |
| `promopack` + `stamped` | `regular` | **yes** — `pdom` `Np` = base + stamp | 22 prints, ~$120 nonfoil / ~$194 foil (Cabal Stronghold `238p` ~$21, Helm of the Host `217p`, Blackblade Reforged `211p`); ONE/NEO/TDM `stamped` rule |
| `fnm` / `league` / `storechampionship` / `openhouse` / `draftweekend` | — | promo-only copies of base cards | 7 prints (Llanowar Elves 168 open house ~$10, Cast Down 81 FNM ~$3) |
| `setpromo` | — | marker on every `pdom` print | not a dupe signal |
| `planeswalkerdeck` / `buyabox` | — | unique cards | 270–280 |

No fancy-foil sheet → configured `[dupe_foil] dom = []` (2026-11-08) to enable `mm query missing-set dom`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons. The pricey alt is the datestamped prerelease Mox Amber.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dom = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pdom` promo-pack stamped `Np` | 22 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$120 |
| `pdom` FNM / league / event promos | 7 | **owner's call** — same question as [`war`](war.md) / [`m19`](m19.md) |
| PW-deck 270–279, buy-a-box 280 | 11 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pdom` | prerelease, datestamped (foil) | Mox Amber `224s` |
| `Np` | `pdom` | Promo Pack, stamped | Cabal Stronghold `238p` |
| `60`, `81`, `204` | `pdom` | FNM (inverted, foil) | Cast Down 81 |
| `76` | `pdom` | Draft Weekend | Zahid, Djinn of the Lamp |
| `168` | `pdom` | Open House | Llanowar Elves |
| `182` | `pdom` | Store Championship | Steel Leaf Champion |
| `249` | `pdom` | League | Zhalfirin Void |
| `270`–`279` | `dom` | Planeswalker Decks | Teferi, Timebender 270 |
| `280` | `dom` | Buy-a-Box | Firesong and Sunspeaker |

---

## 7. Edge cases & gotchas

- **Buy-a-Box card lives in the parent set** (`dom` 280) and is a unique card.
  Compare [`rix`](rix.md), where the Buy-a-Box Captain's Hook is an alt-art
  `prix` foil of a regular booster card.
- **`pdom` is one card short locally** (117 vs Scryfall's 118).
- **20 basics** (four arts per type) at 250–269, in boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dom = []` — configured 2026-11-08 (enables `mm query missing-set dom`).
- `config/families.toml` `[[unobtainable.dom.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.dom]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme boosters ×5 | theme booster | one per colour |
| Planeswalker Decks ×2 | Planeswalker deck | Teferi / Chandra; cards at 270–279 |
| Booster Battle Pack | two-player pack (MTGJSON `multiple_decks` / `battle_pack`) | — |
| Arena Starter Decks ×10 | Arena starter deck | — |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dom --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$5.43, 99.9% coverage |
| `theme-<colour>` | EV ~$8.73 (W) – ~$15.32 (B) |
| `prerelease` / `showdown` | ~$11.57 / ~$5.27 |
| `arena` | digital code card, ignore |
