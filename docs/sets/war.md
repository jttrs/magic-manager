# `war` — War of the Spark

> Per-family memory doc. Read this before answering set-specific questions about
> `war` or working on `war`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `war`
**Family root type:** `expansion`
**Family released:** 2019-05-03
**Last audit:** 2026-11-05 via `/characterize-set war` (one-at-a-time run — tier decisions pending owner review).

---

> **37 planeswalkers, one per booster.** No Collector Booster, no showcase /
> extended-art / borderless treatments in English. The alt-art prints are the
> **Japanese alternate-art planeswalkers** (`war` `N★`), which the local
> English catalog doesn't hold (§7). The WAR Mythic Edition planeswalkers live
> in `med` (Mythic Edition), a separate family.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `war` | expansion | 311 on Scryfall / 276 local | 2019-05-03 | parent — booster set 1–264, PW-deck 265–274, buy-a-box 275, 1 `A-` Alchemy rebalance; Scryfall also lists the Japanese `N★` alt-art planeswalkers |
| `pwar` | promo | 176 on Scryfall / 140 local | 2019-05-03 | prerelease `Ns` datestamped (88) + Promo Pack `Np` stamped (44) + FNM / in-store / open-house / resale |
| `twar` | token | 19 | 2019-05-03 | tokens |

`set:war+related` covers all three. No commander or masterpiece child.

---

## 2. Treatments

Survey (`survey_treatment_signature.py WAR`, 743 print-rows by finish).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 264 | `war` 1–264 (116 C / 80 U / 53 R / 15 M; basics 250–264) | `regular` | rarity/base sub-selectors — R+M ≈ $191 nonfoil / $318 foil (Nicol Bolas, Dragon-God 207 ~$35) |
| Planeswalker-deck exclusives | 10 | `war` 265–274 (Gideon, the Oathsworn 265 + Jace, Arcane Strategist 270, both foil-only, + 4 deck cards each incl. 2 guildgates) | `regular` | **mostly unique cards** — keep; ~$9 total |
| buy-a-box | 1 | `war` 275 Tezzeret, Master of the Bridge (foil-only) | `regular` | **unique card** — keep; ~$17 |
| Japanese alt-art planeswalkers | ~35 | `war` `N★` (Ajani 184★, Gideon Blackblade 13★, …) | — | **not in the local catalog** (Japanese-language prints) — never reach missing-set |
| Alchemy rebalance | 1 | `war` `A-*` | — | dropped by `_is_digital_only` |
| FNM inverted uncommons | 3 | `pwar` 41, 171, 193 (`fnm`, `inverted`, foil) | `b` | promo — Augur of Bolas, Paradise Druid, Dovin's Veto |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 88 prints, auto-dropped (Finale of Devastation `160s` foil ~$87) |
| `promopack` + `stamped` | `regular` | **yes** — `pwar` `Np` = base + stamp | 44 prints, ~$192 nonfoil / ~$283 foil (Finale of Devastation `160p` ~$52); ONE/NEO/TDM `stamped` rule |
| `fnm` / `instore` / `draftweekend` / `openhouse` / `resale` | — | promo-only copies of base cards | 8 prints (Bolas's Citadel 79 draft weekend, Time Wipe 223 / Karn's Bastion 248 in-store, Liliana's Triumph 98 open house, Neheb `140★` resale) |
| `setpromo` | — | marker on every `pwar` print | not a dupe signal by itself |
| `planeswalkerdeck` / `buyabox` | — | unique cards | 265–275 |

No fancy-foil sheet → proposed `[dupe_foil] war = []` to enable `mm query missing-set war`.

**Full-art convention:** none.

---

## 3. Chase variants

None among uncommons in English. The Japanese alt-art planeswalkers are the
set's famous chase, but they're outside the local catalog.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] war = []` | 0 | **apply** — empty, enables missing-set |
| `pwar` promo-pack stamped `Np` | 44 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$192 |
| `pwar` FNM / in-store / open-house / resale | 8 | **owner's call** — promo-only copies; `promo_types_any_of = ["fnm","instore","openhouse","resale"]` if excluded (~$28 foil) |
| PW-deck 265–274, buy-a-box 275 | 11 | keep — real cards |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pwar` | prerelease, datestamped (foil) | Finale of Devastation `160s` |
| `Np` | `pwar` | Promo Pack, stamped | Finale of Devastation `160p` |
| `41`, `171`, `193` | `pwar` | FNM (inverted, foil) | Paradise Druid 171 |
| `79` | `pwar` | Draft Weekend / in-store | Bolas's Citadel |
| `223`, `248` | `pwar` | in-store | Time Wipe |
| `98` | `pwar` | Open House | Liliana's Triumph |
| `140★` | `pwar` | resale | Neheb, Dreadhorde Champion |
| `265`–`274` | `war` | Planeswalker Decks | Jace, Arcane Strategist 270 |
| `275` | `war` | Buy-a-Box | Tezzeret, Master of the Bridge |
| `N★` | `war` | Japanese boosters (alt-art planeswalkers) | Gideon Blackblade 13★ |

---

## 7. Edge cases & gotchas

- **Local catalog has 276 of Scryfall's 311 `war` prints** (and 140 of 176 `pwar`). The `war` gap is the
  Japanese alternate-art `N★` planeswalkers. They won't appear in missing-set,
  Collection or a checklist; add one by hand if owned. The `jp` booster EV
  (96.6% coverage) is understated for the same reason.
- **`★` means two things in this family:** Japanese alt art in `war`, resale in
  `pwar` (`140★`).
- PW-deck planeswalkers and the buy-a-box Tezzeret are foil-only; their deck
  mates are nonfoil only.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.war.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.war]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters (+ Japanese) | booster product | no Collector Booster |
| Theme boosters ×5 | theme booster | W/U/B/R/G |
| Planeswalker Decks ×2 | Planeswalker deck | Gideon / Jace; cards at 265–274 |
| War of the Spark Mythic Edition | Box Set (MTGJSON) | cards in `med`, its own family |
| Bundle | Bundle | Bundle Land Pack (pool); no bundle promo card |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py war --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` / `jp` | EV ~$5.93 / ~$5.22 (jp understated, §7) |
| `theme-{w,u,b,r,g}` | EV ~$7.83–$16.36 (blue highest) |
| `prerelease` / `showdown` | ~$7.05 / ~$8.25 |
| `arena` | digital code card, ignore |
