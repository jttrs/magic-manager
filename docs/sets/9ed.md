# `9ed` — Ninth Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `9ed` or working on `9ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `9ed`
**Family root type:** `core`
**Family released:** 2005-07-29
**Last audit:** 2026-11-06 via `/characterize-set 9ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, pre-mythic, with a full finish split.** Every booster card is
> two Scryfall printings: nonfoil at CN `N`, foil at CN `N★` (same art). Nine
> Starter Deck exclusives sit at `S1`–`S10`. Same pattern as [`10e`](10e.md),
> but for the whole set.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `9ed` | core | 709 local (Scryfall 710) | 2005-07-29 | parent — nonfoil 1–350 (basics 331–350) + foil `1★`–`350★` + Starter Deck `S1`–`S10` |
| `p9ed` | promo | 1 local (Scryfall 2) | 2005-07-29 | release Force of Nature `242★` (same art) |

`set:9ed+related` covers both. No token set. `core` isn't in
`DEFAULT_INVENTORY_SET_TYPES`, but the anchor is always included by
`mm set master-list 9ed`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| nonfoil booster cards | 350 | `9ed` 1–350 (130 C / 110 U / 110 R; 20 basics 331–350) | `regular` | rarity/base sub-selectors — rares ≈ $346 |
| **foil booster cards** | 350 | `9ed` `1★`–`350★` (same split) | `regular` | **same art as `N`** (350/350) — rares ≈ $1,803 foil (Fellwar Stone `297★` ~$207, Biorhythm `231★` ~$105, Grave Pact `135★` ~$90, Seething Song `216★` ~$89) |
| Starter Deck exclusives | 9 | `9ed` `S1`–`S10` (no S6; 6 C / 2 U / 1 R, nonfoil, `starterdeck`) | `regular` | keep — real cards (Vizzerdrix S7) ≈ $1.60 |

**`promo_types` dupe-foil / stamped signals:** `starterdeck` marks S-cards;
the `p9ed` release foil is same-art with no dupe signal. No fancy-foil sheet →
proposed `[dupe_foil] 9ed = []` to enable `mm query missing-set 9ed`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 9ed = []` | 0 | **apply** — empty, enables missing-set |
| `N★` foil halves | 350 | **owner's call** — same art as `N`; owning one finish leaves the other "missing". Same finish-split pattern as `10e` |
| Starter Deck `S` cards | 9 | keep — real cards |
| `p9ed` 242★ | 1 | **owner's call** — same art, no dupe signal |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `242★` | `p9ed` | release (same art) | Force of Nature |
| `S1`–`S10` | `9ed` | Starter Deck | Vizzerdrix S7 |

---

## 7. Edge cases & gotchas

- **Every card is two printings** (nonfoil `N`, foil `N★`), so distinct-printing
  counts are double the card count and any finish-blind "missing" list shows
  both. Match CN **and** finish.
- **No mythics**: rare-regular is the top sub-selector.
- Starter Deck CNs skip `S6`.
- MTGJSON: 5 Theme Decks, 2 Starter Decks, 3 Welcome Boosters, 2 Advanced
  Packs, a Bundle Land Pack, MTGO Redemption — none in `PRECON_MODERN_TYPES`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.9ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.9ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | foils at `N★` |
| Theme Decks ×5 / Starter Decks ×2 | theme / starter deck | Starter Decks carry the `S` cards |
| Fat Pack | Bundle | Bundle Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 9ed --list-boosters` (2026-11-06): `draft` EV ~$8.46.
