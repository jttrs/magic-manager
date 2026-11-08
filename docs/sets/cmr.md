# `cmr` — Commander Legends

> Per-family memory doc. Read this before answering set-specific questions about
> `cmr` or working on `cmr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `cmr`
**Family root type:** `draft_innovation`
**Family released:** 2020-11-20
**Last audit:** 2026-11-04 via `/characterize-set cmr` (one-at-a-time run — tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cmr` | draft_innovation | 718 | 2020-11-20 | parent — booster set 1–361, Commander-deck cards 362–511, borderless PWs 512–513, foil-etched 514–614, ext 615–716, promos 721–722 |
| `pcmr` | promo | 6 | 2020-11-20 | Promo Pack `Np` stamped |
| `tcmr` | token | 23 | 2020-11-20 | tokens (14 full-art) |

`set:cmr+related` covers the family; no `--only` needed. The two Commander
decks live INSIDE `cmr` (CN 362–511), not in a separate commander set.

---

## 2. Treatments

Survey (`survey_treatment_signature.py CMR`, 747 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| booster set | 361 | `cmr` 1–361 (foil + nonfoil; CN 1 The Prismatic Piper is rarity `special`) | `regular` | rarity/base sub-selectors |
| Commander-deck cards | 150 | `cmr` 362–511 (nonfoil; face commanders Wyleth 362 / Aesi 365 foil-only) | `regular` | rarity/base sub-selectors — deck-only cards, no booster twin |
| **borderless planeswalkers** | 2 | `cmr` 512 Tevesh Szat, 513 Jeska (`boosterfun`, no frame effects) | `regular` (borderless without `inverted` computes no `b`) | **kept (default) — pending owner review.** Distinct art from base 153 / 186; because they compute `regular`, mythic-regular lists them beside the base print (~$14 nonfoil) |
| foil-etched (booster legends) | 69 | `cmr` 546–614 (`etched`+`inverted`) | `b\|ff` [etched] | auto-dropped — same art as the booster-set print |
| **foil-etched "legends of the past" (etched-only)** | 32 | `cmr` 514–545 (Akiri, Brago, Derevi, Karador, Karametra, …; mythic, etched only) | `b\|ff` [etched] | auto-dropped as etched — **but these have NO other `cmr` printing**, so missing-set never lists them at all. Reprints of older legends found only in Collector Boosters; owner decision whether that's desired |
| Prismatic Piper etched | 1 | `cmr` 546 (rarity `special`) | `b\|ff` | auto-dropped |
| extended-art | 102 | `cmr` 615–716 (all rarities) | `ext` | auto-dropped — same art as base (102/102); ~$878 nonfoil / ~$1,748 foil (Jeweled Lotus 695, Vampiric Tutor 656) |
| buy-a-box | 1 | `cmr` 721 Mana Confluence (foil) | `regular` | mythic-regular |
| prerelease | 1 | `cmr` 722 Sengir, the Dark Baron (foil, not datestamped) | `regular` | rare-regular |
| promo-pack stamped | 6 | `pcmr` 27p/107p/141p/305p/349p/361p | `regular` | base + stamp dupes, ~$125 nonfoil |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `promopack` + `stamped` | `regular` | yes | 6 prints; `stamped` rule |
| `boosterfun` | — | n/a | ext band + 512–513 |
| `buyabox` / `prerelease` | — | distinct | 721 / 722 |

No fancy-foil sheet → configured `[dupe_foil] cmr = []` (2026-11-08) to enable `mm query missing-set cmr`.

**Full-art convention:** `full_art = 1` only on 14 `tcmr` tokens.

---

## 3. Chase variants

None. `set:cmr+related missing rarity=uncommon treatment=regular chase` → 0 rows.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cmr = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pcmr` promo-pack stamped | 6 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$125 |
| borderless PWs 512–513 | 2 | keep — distinct art |
| etched-only legends 514–545 | 32 | **unsure** — currently invisible to missing-set (etched auto-drop) though they're the only `cmr` print of each card. Leaving it is the cheap default; surfacing them needs a code change, not config |
| ext 615–716 | 102 | n/a — auto-dropped |

**Scarcity check:** not run yet (written before `[dupe_foil]` was added). The dropped ext
band holds most of the family's alt-$ (Jeweled Lotus ext ~$70 / ~$236 foil).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Np` | `pcmr` | Promo Pack, stamped | Opposition Agent 141p |
| `721` | `cmr` | Buy-a-Box (foil) | Mana Confluence |
| `722` | `cmr` | prerelease (foil) | Sengir, the Dark Baron |

---

## 7. Edge cases & gotchas

- **Rarity `special`:** The Prismatic Piper (1, 546) — skipped by missing-set's
  rare/mythic sub-selectors (see [`tsr`](tsr.md) for the same blind spot).
- **Borderless ≠ `b` here:** 512–513 are borderless but carry no `inverted`
  frame effect, so they compute `regular`.
- **Commander decks are inside `cmr`** (Arm for Battle — Wyleth 362; Reap the
  Tides — Aesi 365), nonfoil except the foil face commanders.
- No CN 717–720.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cmr = []` — configured 2026-11-08 (enables `mm query missing-set cmr`).
- `config/families.toml` `[[unobtainable.cmr.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.cmr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander decks ×2 | Commander deck | Arm for Battle (Wyleth) / Reap the Tides (Aesi), cards in `cmr` 362–511 |
| Draft / Collector boosters | booster product | Collector Booster carries etched (514–614) + ext (615–716) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py cmr --list-boosters` (2026-11-04):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$12.17, 99.7% coverage |
| `collector` | EV ~$30.73, 80.2% (etched slots unpriced locally) |
