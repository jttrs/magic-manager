# `mid` — Innistrad: Midnight Hunt

> Per-family memory doc. Read this before answering set-specific questions about
> `mid` or working on `mid`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mid`
**Family root type:** `expansion`
**Family released:** 2021-09-24
**Last audit:** 2026-11-04 via `/characterize-set mid` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

10 Scryfall codes, all parented to `mid`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mid` | expansion | 392 | 2021-09-24 | parent — booster set 1–277 (basics 262–277), extras 278–391, 7 `A-` Alchemy rebalances |
| `mic` | commander | 187 | 2021-09-24 | 2 Commander decks (Coven Counters — Leinore; Undead Unleashed — Wilhelt) + ext-art 39–76 |
| `pmid` | promo | 155 | 2021-09-24 | prerelease `Ns` datestamped (84) + Promo Pack `Np` stamped (68) + 3 `resale` |
| `omic` | memorabilia | 2 | 2021-09-24 | thick etched display commanders |
| `tmid` / `tmic` | token | 19 / 11 | 2021-09-24 | tokens |
| `smid` | token | 9 | 2021-09-24 | double-faced substitute cards (full-art) |
| `mmid` | minigame | 3 | 2021-09-24 | minigame inserts |
| `amid` | memorabilia | 81 | 2021-09-24 | Art Series |

**Separately-rooted bonus sheets:** none. `set:mid+related` covers the family.
Note `dbl` (Double Feature, 2022) reprints all of MID 1–267 in a grayscale frame
but is NOT linked to this family — see [`dbl`](dbl.md).

---

## 2. Treatments

Survey (`survey_treatment_signature.py MID`, 858 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 277 | `mid` 1–277 (incl. 51 `sunmoondfc` DFCs) | `regular` | rarity/base sub-selectors |
| showcase full-art basics | 10 | `mid` 268–277 (`fullart`+`inverted`+`showcase`) | `b\|shw` | kept (commons; not in rare/mythic selectors) |
| **borderless planeswalkers** | 3 | `mid` 278–280 (Wrenn and Seven, Arlinn, Teferi) | `b` | **kept (default) — pending owner review.** Distinct art |
| **borderless slow lands** | 5 | `mid` 281–285 (`inverted`) | `b` | **kept (default) — pending owner review.** Distinct art |
| **showcase (sun/moon frame)** | 26 | `mid` 286–311 (`showcase`, 19 are `sunmoondfc`; all rarities) | `shw` | **kept (default) — pending owner review.** Distinct art; ~$20 nonfoil total |
| **showcase legends (black border, inverted)** | 14 | `mid` 312–325 (`inverted`+`legendary`+`showcase`; rare/mythic) | `b\|shw` | **kept (default) — pending owner review.** The black-border showcase is the high-risk class; distinct art; ~$15 nonfoil total |
| extended-art | 55 + 38 | `mid` 326–385, `mic` 39–76 | `ext` | auto-dropped |
| buy-a-box | 1 | `mid` 385 Champion of the Perished (ext, foil) | `ext` | auto-dropped with the ext class |
| bundle | 1 | `mid` 386 Triskaidekaphile (foil) | `regular` | rare-regular |
| promo-pack inverted commons/uncommons | 5 | `mid` 387–391 (`promopack`, `inverted`, black border) | `b` | same art as base (387↔20, 388↔44 Consider, …); not rare/mythic, only the `preferred` sub-selector sees them |
| display commanders | 2 | `omic` 1–2 (`thick`, etched) | `regular` [etched] | display cards |
| Alchemy rebalance | 7 | `mid` `A-*` | — | dropped by `_is_digital_only` |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes — `pmid` `Ns` | auto-dropped (datestamped filter) |
| `promopack` + `stamped` | `regular` | **yes** — 68/68 share art with the `mid` print | leaks via rare/mythic-regular (~$117 nonfoil / ~$138 foil); ONE/NEO/TDM `stamped` rule |
| `promopack` (alone) | `b` | same art as base | `mid` 387–391 — spared by a `stamped`-only rule |
| `buyabox` / `bundle` / `resale` | — | distinct | kept |
| `thick` | etched | n/a | `omic` |

No textured / fancy-foil sheet in this family → proposed `[dupe_foil] mid = []`
just to enable `mm query missing-set mid`.

**Full-art convention:** `full_art = 1` on `mid` 268–277 and `smid` 1–9.

---

## 3. Chase variants

None. `set:mid+related missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None detected.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mid = []` | 0 | **apply** — empty, enables missing-set |
| `pmid` promo-pack stamped `Np` | 68 | **exclude** — `promo_types_any_of = ["stamped"]` (ONE/NEO/TDM precedent); ~$117 |
| showcase sun/moon 286–311 | 26 | keep — cheap, distinct art |
| showcase legends 312–325 (black border) | 14 | keep — cheap, distinct art (confirm visually; this is the class that bit CLB/AFR) |
| borderless 278–285 | 8 | keep — ~$40 nonfoil |
| promo-pack inverted 387–391 | 5 | keep — sub-rare, harmless |

**Scarcity check:** n/a until a `[dupe_foil]` entry exists. By inspection no
tier concentrates the missing $; base rares/mythics (~$155) lead.

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `pmid` | prerelease, datestamped (foil) | — |
| `Np` | `pmid` | Promo Pack, stamped | — |
| resale | `pmid` | resale promos (3) | — |
| `385` | `mid` | Buy-a-Box (ext-art foil) | Champion of the Perished |
| `386` | `mid` | Bundle (foil) | Triskaidekaphile |
| `387`–`391` | `mid` | Promo Pack inverted commons/uncommons | Consider 388 |

---

## 7. Edge cases & gotchas

- **Day/night DFCs:** 59 `sunmoondfc` prints across base, showcase and ext;
  the back face shares the row.
- `mid` 384 is a plain Forest (last basic), not an extra — the extras start at 278
  but CN 384 sits inside the ext band numerically.
- Double Feature (`dbl`) is a separate family; MID completion ignores it.
- Booster EV coverage is ~73–86% for set/collector/draft (some slots unresolved locally).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mid.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mid]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Coven Counters (Leinore, `mic` 1) / Undead Unleashed (Wilhelt, `mic` 2); display commanders `omic` |
| Bundle | Bundle | `mid` 386 promo; Bundle Land Pack in MTGJSON |
| Welcome Booster | Welcome deck | MTGJSON `Welcome Booster` |
| Theme boosters | theme booster | W/U/B/R/G + Werewolves |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mid --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` / `set` | EV ~$3.91 / ~$5.11 (86% / 80% coverage) |
| `collector` | EV ~$10.89, 73.2% |
| `theme-{w,u,b,r,g,werewolves}` | EV ~$5.26–$8.15 |
| `prerelease` / `promo` / `promo-foil` | ~$2.54 / ~$5.81 / ~$7.23 |
| `arena` | digital code card, ignore |
