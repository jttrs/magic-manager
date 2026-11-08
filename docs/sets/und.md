# `und` — Unsanctioned

> Per-family memory doc. Read this before answering set-specific questions about
> `und` or working on `und`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `und`
**Family root type:** `funny` (silver-bordered, not tournament-legal)
**Family released:** 2020-02-29
**Last audit:** 2026-11-04 via `/characterize-set und` (one-at-a-time run — tier decisions pending owner review).

---

> **A fixed-content boxed product of five silver-bordered half-decks**, one per
> colour, shuffled together two at a time for play. Mostly Un-set reprints
> (Unglued / Unhinged / Unstable) plus a few new cards. Standalone
> (`parent_set_code: null`). Cheap: the whole set is about $42 nonfoil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `und` | funny | 96 | 2020-02-29 | parent — 86 silver-border cards (1–86) + 10 basics (87–96) |
| `tund` | token | 6 | 2020-02-29 | tokens |

`set:und+related` covers both.

---

## 2. Treatments

Survey (`survey_treatment_signature.py UND`, 102 prints).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| silver-border cards (nonfoil) | 86 | `und` 1–86 (40 C incl. basics below / 22 U / 30 R / 4 M) | `regular` | rarity sub-selectors — R+M ≈ $11 total; Booster Tutor 33 ~$4, Jack-in-the-Mox 78 ~$2 |
| regular basics (black border) | 5 | `und` 87, 89, 91, 93, 95 | `regular` | basics, never rare/mythic |
| **full-art basics** (black border, foil + nonfoil) | 5 | `und` 88, 90, 92, 94, 96 | `fa` | basics — the only foils in the set, and the priciest rows (~$2–$4 each) |
| tokens | 6 | `tund` | `regular` | tokens |

`frame_effects`: `legendary` 11, `tombstone` 1 — cosmetic. No `promo_types`.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] und = []` to enable `mm query missing-set und`.

**Full-art convention:** full-art basics alternate with regular basics by CN
(even = full art).

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

No rule is active; none needed.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] und = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 96 | **owner's call** — silver-bordered and not tournament-legal; track only if collecting Un-cards |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Card names with punctuation and fragments**: `Humming-` 7, `Bat-` 32,
  `Half-Squirrel, Half-` 65 and `Who // What // When // Where // Why` 75 (a
  five-part split card). Name search needs the exact punctuation.
- **Most cards are reprints** of Unglued / Unhinged / Unstable cards in this
  box. The `und` print is usually not the only one.
- **Rarity is from the original Un-set**, not distribution: every card is in
  the fixed box at fixed quantities, so "mythic" here does not mean scarce.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] und = []` — configured 2026-11-08 (enables `mm query missing-set und`).
- `config/families.toml` `[[unobtainable.und.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.und]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Unsanctioned | box set (MTGJSON `sealedProduct` `multiple_decks` / `game_night`) | 5 half-decks (MTGJSON `type: Halfdeck`: White, Blue, Black, Red, Green) |

**Booster types (for `sealed-value` EV):** none (`sealed_value.py und --list-boosters` → no booster data).
