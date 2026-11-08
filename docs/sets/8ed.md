# `8ed` — Eighth Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `8ed` or working on `8ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `8ed`
**Family root type:** `core`
**Family released:** 2003-07-28
**Last audit:** 2026-11-06 via `/characterize-set 8ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, pre-mythic, with a full finish split.** Every booster card is
> two Scryfall printings: nonfoil at CN `N`, foil at CN `N★` (same art). Seven
> Starter Deck exclusives sit at `S1`–`S7`. Same pattern as [`9ed`](9ed.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `8ed` | core | 707 local (Scryfall 711) | 2003-07-28 | parent — nonfoil 1–350 (basics 331–350) + foil `1★`–`350★` + Starter Deck `S1`–`S7` |
| `p8ed` | promo | 1 local (Scryfall 2) | 2003-07-28 | release Rukh Egg `216★` (same art) |

`set:8ed+related` covers both. No token set. `core` isn't in
`DEFAULT_INVENTORY_SET_TYPES`, but the anchor is always included by
`mm set master-list 8ed`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| nonfoil booster cards | 350 | `8ed` 1–350 (130 C / 110 U / 110 R; 20 basics 331–350) | `regular` | rarity/base sub-selectors — rares ≈ $292 |
| **foil booster cards** | 350 | `8ed` `1★`–`350★` (same split) | `regular` | **same art as `N`** (350/350) — rares ≈ $1,953 foil (Birds of Paradise `233★` ~$319, Grave Pact `137★` ~$225, City of Brass `322★` ~$150, Intruder Alarm `86★` ~$108) |
| Starter Deck exclusives | 7 | `8ed` `S1`–`S7` (3 C / 3 U / 1 R, nonfoil, `starterdeck`) | `regular` | keep — real cards (Vizzerdrix S5, Silverback Ape S7) ≈ $2.10 |

**`promo_types` dupe-foil / stamped signals:** `starterdeck` marks S-cards;
the `p8ed` release foil is same-art with no dupe signal. No fancy-foil sheet →
configured `[dupe_foil] 8ed = []` (2026-11-08) to enable `mm query missing-set 8ed`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 8ed = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `N★` foil halves | 350 | **owner's call** — same art as `N`; owning one finish leaves the other "missing". Same finish-split pattern as `10e` |
| Starter Deck `S` cards | 7 | keep — real cards |
| `p8ed` 216★ | 1 | **owner's call** — same art, no dupe signal |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `216★` | `p8ed` | release (same art) | Rukh Egg |
| `S1`–`S7` | `8ed` | Starter Deck | Vizzerdrix S5 |

---

## 7. Edge cases & gotchas

- **A foil Vizzerdrix `S5a`** (same art as S5) is on Scryfall but not local. Scryfall's search leaves out `variation` prints, so `mm set sync` never fetches them.
- **Every card is two printings** (nonfoil `N`, foil `N★`), so distinct-printing
  counts are double the card count and any finish-blind "missing" list shows
  both. Match CN **and** finish.
- **No mythics**: rare-regular is the top sub-selector.
- **Same `N★` foil split as `9ed` and `10e`.**
- MTGJSON: 5 Theme Decks, 2 Starter Decks, 2 Demo Decks, a Welcome Booster,
  2 Advanced Packs, MTGO Redemption — none in `PRECON_MODERN_TYPES`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] 8ed = []` — configured 2026-11-08 (enables `mm query missing-set 8ed`).
- `config/families.toml` `[[unobtainable.8ed.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.8ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | foils at `N★` |
| Theme Decks ×5 / Starter Decks ×2 | theme / starter deck | Starter Decks carry the `S` cards |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 8ed --list-boosters` (2026-11-06): `draft` EV ~$6.19.
