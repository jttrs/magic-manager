# `cn2` — Conspiracy: Take the Crown

> Per-family memory doc. Read this before answering set-specific questions about
> `cn2` or working on `cn2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `cn2`
**Family root type:** `draft_innovation`
**Family released:** 2016-08-26
**Last audit:** 2026-11-05 via `/characterize-set cn2` (one-at-a-time run — tier decisions pending owner review).

---

> **Multiplayer draft set** with Conspiracy cards and draft-matters cards
> (`frame_effects` `draft`), mixing new cards and reprints (Show and Tell,
> Burgeoning, Berserk). No promo child. One treatment quirk, the same as
> [`bbd`](bbd.md): Kaya, Ghost Assassin has a nonfoil print (75) and a
> foil-only alternate-art print (222).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cn2` | draft_innovation | 222 | 2016-08-26 | parent — CN 1–221 (no basics) + Kaya alt-art foil 222 |
| `tcn2` | token | 12 | 2016-08-26 | tokens |

`set:cn2+related` covers both. `draft_innovation` isn't a default inventory set
type, but the anchor is always included by `mm set master-list cn2`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py CN2`): every print computes `regular`.
`frame_effects` `draft` (27 prints: 12 Conspiracies + 15 draft-matters cards)
is a frame marker, not a treatment.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 220 | `cn2` 1–221 minus 75 (90 C / 67 U / 50 R / 13 M) | `regular` | rarity/base sub-selectors — R+M ≈ $219 nonfoil / $805 foil (Burgeoning 178 ~$33, Show and Tell 121 ~$19 / $41, Expropriate 30 ~$15 / $51, Horn of Greed 211 ~$16) |
| Conspiracies | 12 | `cn2` 1–12 (type `Conspiracy`, `draft` frame; included in the base row) | `regular` | part of base; not constructed-legal |
| Kaya, nonfoil | 1 | `cn2` 75 (nonfoil-only, mythic; draft sheet `nonconspiracyRareMythic`) | `regular` | mythic-regular |
| Kaya, alt-art foil | 1 | `cn2` 222 (foil-only, **different art** from 75; draft sheet `nonconspiracyFoil`) | `regular` | **not a dupe** — distinct illustration, keep; ~$28 |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] cn2 = []` to enable `mm query missing-set cn2`.

**Full-art convention:** none.

---

## 3. Chase variants

Kaya 222 (alt-art foil) is the only alternate print.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cn2 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| Kaya alt-art foil 222 | 1 | keep — booster card with its own art |

---

## 6. PRM destinations

n/a — no promo child (no prerelease, Promo Pack or buy-a-box prints in
Scryfall).

---

## 7. Edge cases & gotchas

- **Same card, two arts, split by finish** (as in `bbd`): Kaya 75 is
  nonfoil-only with the art reused by `plst` CN2-75; Kaya 222 is foil-only
  with its own art. A "missing foil Kaya" means 222.
- **Conspiracies are not legal in constructed** but are real collectible
  cards; selectors treat them like any other card.
- **No basics** in the set; MTGJSON's draft booster has dedicated conspiracy
  and conspiracy-foil sheets.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cn2 = []` — configured 2026-11-08 (enables `mm query missing-set cn2`).
- `config/families.toml` `[[unobtainable.cn2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cn2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | conspiracy slot |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py cn2 --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$6.75, 99.8% coverage |
