# `rna` — Ravnica Allegiance

> Per-family memory doc. Read this before answering set-specific questions about
> `rna` or working on `rna`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rna`
**Family root type:** `expansion`
**Family released:** 2019-01-25
**Last audit:** 2026-11-05 via `/characterize-set rna` (one-at-a-time run — tier decisions pending owner review).

---

> **Five-guild Ravnica set, base frame only.** No showcase, extended-art or
> borderless prints. Extras are the Planeswalker Deck cards and a buy-a-box
> card. Related products in other families: the Guild Kits ([`gk2`](gk2.md))
> and the RNA Mythic Edition planeswalkers (`med`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rna` | expansion | 273 | 2019-01-25 | parent — booster set 1–259, PW-deck basics 260–264, PW-deck cards 265–272, buy-a-box 273 |
| `prna` | promo | 81 | 2019-01-25 | prerelease `Ns` datestamped (40) + Promo Pack `Np` stamped (33) + FNM / league / store championship / open house / draft weekend / resale (8) |
| `prw2` | promo | 10 | 2019-01-25 | RNA Ravnica Weekend guild basics, CN `B01`–`B10` (foil-only) |
| `trna` | token | 13 | 2019-01-25 | tokens |

`set:rna+related` covers all four.

---

## 2. Treatments

Survey (`survey_treatment_signature.py RNA`, 674 print-rows by finish).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 259 | `rna` 1–259 (111 C / 80 U / 53 R / 15 M; guildgates ×2 per guild 250–258, Stomping Ground 259 ~$8) | `regular` | rarity/base sub-selectors — R+M ≈ $165 nonfoil / $337 foil (Smothering Tithe 22 ~$56) |
| PW-deck basics | 5 | `rna` 260–264 (`planeswalkerdeck`, foil + nonfoil) | `regular` | basics |
| Planeswalker-deck exclusives | 8 | `rna` 265 Dovin, Architect of Law + 266–268; 269 Domri, City Smasher + 270–272 | `regular` | **unique cards** — keep; walkers foil-only, deck mates nonfoil-only; ~$3 |
| buy-a-box | 1 | `rna` 273 The Haunt of Hightower (foil-only) | `regular` | **unique card** — keep; ~$5 |
| Ravnica Weekend basics | 10 | `prw2` `B01`–`B10` (two per guild, foil-only) | `regular` | basics, never rare/mythic; ~$31 foil total |
| FNM inverted | 3 | `prna` 107, 178, 192 (`fnm`, `inverted`, foil) | `b` | promo |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 40 prints, auto-dropped |
| `promopack` + `stamped` | `regular` | **yes** — `prna` `Np` = base + stamp | 33 prints, ~$166 nonfoil / ~$236 foil (Smothering Tithe `22p` ~$57); ONE/NEO/TDM `stamped` rule |
| `fnm` / `league` / `storechampionship` / `openhouse` / `draftweekend` / `resale` | — | promo-only copies of base cards | 8 prints (Lavinia 189 store championship, Simic Ascendancy 207 draft weekend, End-Raze Forerunners `124★` resale) |
| `setpromo` | — | marker on every `prna` print | not a dupe signal |
| `planeswalkerdeck` / `buyabox` | — | unique cards | 260–273 |

No fancy-foil sheet → configured `[dupe_foil] rna = []` (2026-11-08) to enable `mm query missing-set rna`.

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
| `[dupe_foil] rna = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `prna` promo-pack stamped `Np` | 33 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$166 |
| `prna` FNM / league / event promos | 8 | **owner's call** — same question as [`war`](war.md) |
| PW-deck 265–272, buy-a-box 273 | 9 | keep — real cards |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `prna` | prerelease, datestamped (foil) | Biomancer's Familiar `158s` |
| `Np` | `prna` | Promo Pack, stamped | Smothering Tithe `22p` |
| `107`, `178`, `192` | `prna` | FNM (inverted, foil) | Growth Spiral 178 |
| `189` | `prna` | Store Championship | Lavinia, Azorius Renegade |
| `197` | `prna` | Open House | Rakdos Firewheeler |
| `207` | `prna` | Draft Weekend | Simic Ascendancy |
| `232` | `prna` | League | Gate Colossus |
| `124★` | `prna` | resale | End-Raze Forerunners |
| `B01`–`B10` | `prw2` | Ravnica Weekend | Swamp B05 |
| `265`–`272` | `rna` | Planeswalker Decks | Domri, City Smasher 269 |
| `273` | `rna` | Buy-a-Box | The Haunt of Hightower |

---

## 7. Edge cases & gotchas

- **Booster basics don't exist:** RNA packs carry a guildgate slot; the five
  basics 260–264 come from the Planeswalker Decks.
- **`prw2` CNs are letters + digits** (`B01`…); the guild is in the art, not the
  CN. They sort after numeric CNs.
- **Guild-specific products:** prerelease packs and theme boosters are per
  guild (`prerelease-<guild>`, `theme-<guild>`), not per colour.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] rna = []` — configured 2026-11-08 (enables `mm query missing-set rna`).
- `config/families.toml` `[[unobtainable.rna.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.rna]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | guildgate slot instead of a basic |
| Theme boosters ×5 | theme booster | one per guild |
| Planeswalker Decks ×2 | Planeswalker deck | Dovin / Domri; cards at 260–272 |
| Guild Kits ×5 | Guild kit | separate family [`gk2`](gk2.md) |
| Ravnica Allegiance Mythic Edition | Box Set (MTGJSON) | cards in `med`, its own family |
| Bundle / Deck Builder's Toolkit | Bundle / kit | Bundle Land Pack and DBT are pools |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rna --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$4.94, 98% coverage |
| `collector` | EV ~$12.55 (MTGJSON lists one layout) |
| `theme-<guild>` | EV ~$5.57 (Rakdos) – ~$10.17 (Gruul) |
| `prerelease-<guild>` | EV ~$3.35 (Azorius) – ~$10.27 (Simic) |
| `showdown` | ~$6.95 |
| `arena` | digital code card, ignore |
