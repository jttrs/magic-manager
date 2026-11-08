# `grn` — Guilds of Ravnica

> Per-family memory doc. Read this before answering set-specific questions about
> `grn` or working on `grn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `grn`
**Family root type:** `expansion`
**Family released:** 2018-10-05
**Last audit:** 2026-11-05 via `/characterize-set grn` (one-at-a-time run — tier decisions pending owner review).

---

> **First half of the Guilds of Ravnica block, base frame only.** No showcase,
> extended-art or borderless prints. Same structure as its sibling
> [`rna`](rna.md): guildgate slot, Planeswalker Deck band, buy-a-box card,
> Ravnica Weekend basics. Related products in other families: the Guild Kits
> ([`gk1`](gk1.md)) and the GRN Mythic Edition walkers ([`med`](med.md) GR1–GR8).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `grn` | expansion | 273 | 2018-10-05 | parent — booster set 1–259, PW-deck basics 260–264, PW-deck cards 265–272, buy-a-box 273 |
| `pgrn` | promo | 84 | 2018-10-05 | prerelease `Ns` datestamped (40) + Promo Pack `Np` stamped (36) + FNM / league / store championship / open house / draft weekend / resale (8) |
| `prwk` | promo | 10 | 2018-10-05 | GRN Ravnica Weekend guild basics, CN `A01`–`A10` (foil-only) |
| `tgrn` | token | 8 | 2018-10-05 | tokens |

`set:grn+related` covers all four.

---

## 2. Treatments

Survey (`survey_treatment_signature.py GRN`): every print computes `regular`
except 4 FNM / open-house `inverted` promos (`b`).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 259 | `grn` 1–259 (111 C / 80 U / 53 R / 15 M; guildgates ×2 per guild + Guildmages' Forum + the 5 shocklands 253–259 in the land slot) | `regular` | rarity/base sub-selectors — R+M ≈ $120 nonfoil / $318 foil (Sacred Foundry 254 ~$12, Steam Vents 257 / Watery Grave 259 ~$11) |
| PW-deck basics | 5 | `grn` 260–264 (`planeswalkerdeck`, foil + nonfoil) | `regular` | basics |
| Planeswalker-deck exclusives | 8 | `grn` 265 Ral, Caller of Storms + 266–268; 269 Vraska, Regal Gorgon + 270–272 | `regular` | **unique cards** — keep; walkers foil-only, deck mates nonfoil-only; ~$6 |
| buy-a-box | 1 | `grn` 273 Impervious Greatwurm (foil-only) | `regular` | **unique card** — keep; ~$5 |
| Ravnica Weekend basics | 10 | `prwk` `A01`–`A10` (two per guild, foil-only) | `regular` | basics, never rare/mythic; ~$20 foil total |
| FNM / open-house inverted | 4 | `pgrn` 6, 54, 206 (`fnm`), 156 (`openhouse`) | `b` | promo |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 40 prints, auto-dropped (Hatchery Spider `132s` ~$17) |
| `promopack` + `stamped` | `regular` | **yes** — `pgrn` `Np` = base + stamp | 36 prints, ~$130 nonfoil / ~$226 foil (shockland `Np`s ~$13 each); ONE/NEO/TDM `stamped` rule |
| `fnm` / `league` / `storechampionship` / `openhouse` / `draftweekend` / `resale` | — | promo-only copies of base cards | 8 prints (Emmara 168 store championship, Firemind's Research 171 draft weekend, Beast Whisperer `123★` resale) |
| `setpromo` | — | marker on every `pgrn` print | not a dupe signal |
| `planeswalkerdeck` / `buyabox` | — | unique cards | 260–273 |

No fancy-foil sheet → configured `[dupe_foil] grn = []` (2026-11-08) to enable `mm query missing-set grn`.

**Full-art convention:** none.

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
| `[dupe_foil] grn = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pgrn` promo-pack stamped `Np` | 36 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$130 |
| `pgrn` FNM / league / event promos | 8 | **owner's call** — same question as [`war`](war.md) / [`rna`](rna.md) |
| PW-deck 265–272, buy-a-box 273 | 9 | keep — real cards |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pgrn` | prerelease, datestamped (foil) | Hatchery Spider `132s` |
| `Np` | `pgrn` | Promo Pack, stamped | Watery Grave `259p` |
| `6`, `54`, `206` | `pgrn` | FNM (inverted, foil) | Thought Erasure 206 |
| `79` | `pgrn` | League | Necrotic Wound |
| `156` | `pgrn` | Open House (inverted) | Boros Challenger |
| `168` | `pgrn` | Store Championship | Emmara, Soul of the Accord |
| `171` | `pgrn` | Draft Weekend | Firemind's Research |
| `123★` | `pgrn` | resale | Beast Whisperer |
| `A01`–`A10` | `prwk` | Ravnica Weekend | Mountain A04 |
| `265`–`272` | `grn` | Planeswalker Decks | Vraska, Regal Gorgon 269 |
| `273` | `grn` | Buy-a-Box | Impervious Greatwurm |

---

## 7. Edge cases & gotchas

- **Booster basics don't exist:** the land slot is guildgates + Guildmages'
  Forum + shocklands; the basics 260–264 come from the Planeswalker Decks.
- **Ravnica Weekend codes:** GRN's are `prwk` `A01`–`A10`, RNA's are `prw2`
  `B01`–`B10` — two different set codes for the same program.
- Guild-specific prerelease packs and theme boosters (`prerelease-<guild>`,
  `theme-<guild>`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] grn = []` — configured 2026-11-08 (enables `mm query missing-set grn`).
- `config/families.toml` `[[unobtainable.grn.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.grn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | guildgate / shockland land slot |
| Theme boosters ×5 | theme booster | one per guild |
| Planeswalker Decks ×2 | Planeswalker deck | Ral / Vraska; cards at 260–272 |
| Guild Kits ×5 | Guild kit | separate family [`gk1`](gk1.md) |
| Guilds of Ravnica Mythic Edition | Box Set (MTGJSON) | walkers in [`med`](med.md) GR1–GR8 |
| Arena Starter Deck *Wing and Claw* | Arena starter deck | — |
| Bundle | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py grn --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$3.91, 98% coverage |
| `theme-<guild>` | EV ~$5.83 (Selesnya) – ~$7.49 (Golgari) |
| `prerelease-<guild>` | EV ~$3.32 (Boros) – ~$7.04 (Golgari) |
| `showdown` | ~$5.50 |
| `arena` | digital code card, ignore |
