# `cmm` — Commander Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `cmm` or working on `cmm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `cmm`
**Family root type:** `masters` (Commander-focused reprint set — no expansion parent)
**Family released:** `2023-08-04`
**Last audit:** `2026-11-02` via `/characterize-set cmm` (non-interactive batch run — tier decisions pending owner review).

---

## 1. Family map

3 Scryfall codes, linked via `parent_set_code`. Unusually, the four Commander
precons are **not** a separate `cmc`-style child set — every deck card lives
inside `cmm` itself (CN 704–1056), so the one code holds booster cards,
collector-booster treatments AND precon decklists.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cmm` | masters | 1067 | 2023-08-04 | parent — booster set + 4 precons + collector treatments; CN bands in §2 |
| `tcmm` | token | 81 | 2023-08-04 | tokens (Spirit, Dragon, Elemental, Construct ×N art variants, …); `tcmm` 42 Construct is the only `full_art` token |
| `acmm` | memorabilia | 81 | 2023-08-04 | Art Series (no promo_types, borderless, unpriced) — see §7 leak note |

**Separately-rooted bonus sheets:** none. The `/sets` scan 2023-07-15 → 2023-09-15
shows only unrelated products (`ph22`, `ea3`/`ha7`, `p30t`, the WOE family,
`ptsr`, `pmda`). No `pcmm` (prerelease) or `ocmm` exists.

`mm set master-list cmm` / `set:cmm+related` resolve the whole family from the
parent — no `--only` needed. `tcmm` is excluded from master-list by default
(`token`); `acmm` by default (`memorabilia`).

**CN band map of `cmm`** (verified against the local `cards` table):

| CN | Count | What | Finishes |
|---|---:|---|---|
| 1–451 | 451 | booster set (1 special Prismatic Piper, 145 C / 135 U / 135 R / 35 M; 437–451 = 3 arts × 5 basics) | foil+nonfoil (Piper nonfoil) |
| 452–621 | 170 | **foil-etched** twins of booster rares/mythics (collector booster) | etched |
| 622–667 | 46 | borderless (`inverted`) staples | foil+nonfoil |
| 668–691 | 24 | borderless **profile/portrait** legends (`portrait`) | foil+nonfoil |
| 692–703 | 12 | borderless **full-art** staples (`full_art: true` — Demonic Tutor, Jeweled Lotus, Deflecting Swat, Smothering Tithe, Sol Ring, …) | foil+nonfoil |
| 704–711 | 8 | precon face + secondary commanders (Zhulodok, Anikthea, Commodore Guff, Sliver Gravemother; Omarthis, Narci, Leori, Rukarumel) | foil only |
| 712–743 | 32 | new-to-Commander precon cards | nonfoil only |
| 744–778 | 35 | **extended-art** twins of 712–743 (28) + of the 7 legend commanders | foil+nonfoil |
| 779–782 | 4 | `thick` oversized-display etched face commanders | etched |
| 783–1056 | 274 | precon reprints (incl. basics 783+) | nonfoil only |
| 1057–1066 | 10 | **textured foil** of 9 portrait legends + Jeweled Lotus | foil only |
| 1067 | 1 | Disrupt Decorum `release` promo (distinct art from its booster print) | foil only |

---

## 2. Treatments

`promo_types` is almost entirely the `boosterfun` umbrella (297), with
`portrait` (33), `textured` (10), `thick` (4), `release` (1). The structure lives
in `frame_effects` / `finishes` / `border_color`:

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 451 + 32 + 274 + 8 | 1–451, 704–743, 783–1056 | `regular` | handled by rarity/base sub-selectors (deck-only nonfoil reprints included — see §7) |
| etched (foil-etched, black border, `inverted+etched`) | 170 + 4 thick | 452–621, 779–782 | `b\|ff` [etched] | never reaches missing-set output (verified by simulation: 0 etched rows). 169/170 share art with the booster print; **Ezuri's Predation 558** has different art from 287 |
| borderless (`inverted`) | 46 + 12 full-art | 622–667, 692–703 | `b` | **KEPT (default) — pending owner review.** Distinct art from the booster prints (0 illustration matches). The full-art 692–703 sub-band (`full_art: true`) also computes `b`, not `fa` |
| borderless profile/portrait (`portrait`, `legendary+inverted`) | 24 | 668–691 | `b` | **KEPT (default) — pending owner review.** Distinct art |
| textured foil (`textured`) | 10 | 1057–1066 | `b\|ff` [foil] | **same art** as the portrait borderless (9) / full-art Jeweled Lotus 702 (1) → dupe-foil (configured `[dupe_foil] cmm = ["textured"]` (2026-11-08); collapses in step 3). Unconfigured, it is the family's scarcity tier (~$1,276 foil, Jeweled Lotus 1066 $628, The Ur-Dragon 1065 $237) |
| extended-art | 35 | 744–778 | `ext` | auto-dropped by `preferred` (ext class); same art as 712–743 / the commander faces |
| release promo | 1 | 1067 | `b` [foil] | kept — Disrupt Decorum, distinct art |
| showcase | 0 | — | — | none in this family |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `ext` / `b\|ff` | n/a (umbrella) | tags borderless, ext and etched bands |
| `portrait` | `b` | no — unique art | the profile-legend borderless; also on 9 of the 10 textured prints |
| `textured` | `b\|ff` | **yes** — same illustration as the portrait/full-art borderless sibling (10/10) | → `[dupe_foil] cmm = ["textured"]` (proposed) |
| `thick` | `b\|ff` [etched] | yes (display-size copies of 704/705/706/707 commanders) | oversized display cards; not in missing output |
| `release` | `b` | no — unique art | 1067 Disrupt Decorum, foil only |

**Full-art convention:** `full_art` TRUE only on the 12 borderless full-art
staples 692–703, textured Jeweled Lotus 1066, and `tcmm` 42 Construct (`fa`).
**Security stamp:** 619 `cmm` prints oval-stamped; tokens/art cards none.

---

## 3. Chase variants

No multi-art booster chase. `missing rarity=uncommon treatment=regular chase` → 0
rows. `set:cmm+related chase` (73 rows) is only **basic lands** (booster basics
437–451 = 3 arts each; precon basics from 783) and **token art variants**
(`tcmm` Spirit / Dragon / Elemental / Construct ×3+).

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Plains / Island / Swamp / Mountain / Forest | 3 each (booster) | `cmm` 437–451 | common | regular |

Many legends appear 3–4× (base / etched / portrait borderless / textured — e.g.
Kozilek, the Great Distortion 2 / 452 / 668 / 1057) but those are the normal
treatment ladder, not a same-treatment chase.

---

## 4. Scenes / posters / panoramas

**None.** The borderless bands are individual reprints by many artists; no
`poster` promo_type, no single-artist contiguous run. Not encoded in
`[[scenes.cmm]]`.

---

## 5. Unobtainable rules

**No rule is active.**

| Tier | Disposition | Rationale |
|---|---|---|
| borderless (`inverted`, 622–667 + full-art 692–703) | kept (default) — pending owner review | Distinct art, the family's main collector tier (58 prints, ~$1,143 nonfoil missing incl. portrait). Recommend keep |
| borderless portrait legends (668–691) | kept (default) — pending owner review | Distinct profile art of the set's commanders. Recommend keep |
| textured foil (1057–1066) | handled by configured `[dupe_foil] cmm = ["textured"]` (2026-11-08) | Same art as the portrait/full-art borderless; scarcity tier. If dupe-foil is NOT adopted, an `unobtainable` rule `promo_types_any_of = ["textured"]` is the equivalent |

**Missing-set baseline (simulated 2026-11-02, local prices, nothing configured
in families.toml — config injected in-process):**
- `[dupe_foil] cmm = []` → **422 prints / ~$4,167** (top: Jeweled Lotus textured 1066 $628, The Ur-Dragon textured 1065 $237, Deflecting Swat 698 $103, Demonic Tutor 696 $93).
- `[dupe_foil] cmm = ["textured"]` → **412 prints / ~$2,891**, a flat curve topped by full-art borderless staples (Deflecting Swat 698, Demonic Tutor 696, Jeweled Lotus 702, Fierce Guardianship 694). Breakdown: booster regular 169 / $1,397; borderless 82 / $1,143; precon reprints 59 / $148; precon-new 16 / $124; foil faces 4 / $73; release 1 / $5; plus 81 unpriced `acmm` art cards (§7).

**Scarcity check:** `scripts/set_status.py cmm` printed no ⚠ concentration note
(missing figures show "cross-set; n/a" until `[dupe_foil]` is configured).

---

## 6. PRM destinations

**None in-family.** There is no `pcmm` prerelease/promo-pack set — CMM had no
prerelease. The only promo is `cmm` 1067 Disrupt Decorum (`release`, foil) in
the parent itself. A CMM card with a different stamp belongs to another
channel (Secret Lair, WPN), not this family.

---

## 7. Edge cases & gotchas

- **Precons live inside `cmm`.** The 4 Commander decks (MTGJSON
  `EldraziUnbound_CMM`, `EnduringEnchantments_CMM`, `PlaneswalkerParty_CMM`,
  `SliverSwarm_CMM`) are CN 704–1056 of the parent, not a child set. Their
  nonfoil-only reprints (783–1056) are distinct printings, so the rare-/
  mythic-regular sub-selectors list them beside the booster copy of the same
  card (59 prints / ~$148 missing) — buying the precon is the practical fill.
- **Art Series leaks into missing-set.** `set:cmm+related` (and thus
  `missing.missing_printings`) includes `acmm`: 81 unpriced art cards compute
  `b` and survive `preferred`. `_drop_tokens` doesn't catch them (`is_token=0`)
  and no `[[unobtainable]]` rule key can target a set code. Generic pipeline
  issue (flagged, not papered over here).
- **Full-art borderless computes `b`, not `fa`** — 692–703 are `full_art: true`
  but `compute_treatment` reports `b` (border wins).
- **Etched band computes `b`** (`inverted` frame) despite `border_color: black`.
- **Ezuri's Predation** etched 558 uses different art from booster 287 — the one
  etched print that isn't a same-art twin.
- **Commodore Guff** 706/781 carries no `legendary` frame effect (planeswalker
  frame), unlike the other face commanders.
- **No arena leak** — `set:cmm+related missing | grep -i arena` → 0.
- **The Prismatic Piper** `cmm` 1 is rarity `special`, nonfoil only.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cmm = ["textured"]` — configured 2026-11-08 (enables `mm query missing-set cmm`).
- `config/families.toml` `[[unobtainable.cmm.rules]]` — None configured yet (proposals pending owner review).
- `[[scenes.cmm]]` — not configured (no scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Commander Deck ×4 | Commander deck | `EldraziUnbound_CMM` (Zhulodok), `EnduringEnchantments_CMM` (Anikthea), `PlaneswalkerParty_CMM` (Commodore Guff), `SliverSwarm_CMM` (Sliver Gravemother). Cards are `cmm` CN 704–1056 (foil commanders 704–711, nonfoil rest); collector-display `thick` commanders 779–782 |
| Draft / Set / Collector Booster | booster | see below; collector boosters carry etched, borderless, portrait, ext and textured bands |
| Art Series | Art Series | `acmm` (81) — memorabilia, not booster EV |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py cmm --list-boosters`:

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `draft` | EV ~$27.77, coverage 99.8%, 4 layouts |
| `set` | EV ~$29.38, coverage 99.8%, 8 layouts |
| `collector` | EV ~$77.67, coverage 93.2%, 4 layouts (etched prices are not stored locally → lower coverage) |
| `collector-sample` | EV ~$20.83, coverage 100%, 2 layouts |
