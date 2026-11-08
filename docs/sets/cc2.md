# `cc2` — Commander Collection: Black

> Per-family memory doc. Read this before answering set-specific questions about
> `cc2` or working on `cc2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cc2`
**Family root type:** `arsenal`
**Family released:** 2022-01-28
**Last audit:** 2026-11-04 via `/characterize-set cc2` (one-at-a-time run — tier decisions pending owner review).

---

> **A fixed-content box set.** Commander Collection: Black is an 8-card premium
> box of black Commander staples with new art, plus one token. Sold as a
> regular (nonfoil) box and a Premium (foil) box — that is why every card has
> both finishes. Sibling: `cc1` (Commander Collection: Green, 2020), its own family.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cc2` | arsenal | 9 | 2022-01-28 | parent — 8 cards + Snake // Zombie token (CN 9) |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 8 | `cc2` 1–8 | `regular` | rarity/base sub-selectors (2 mythic, 6 rare) |
| token | 1 | `cc2` 9 Snake // Zombie | `regular` | `is_token` — never in buy lists |

No alt treatments, no `promo_types`. CN 1 Liliana is an `originpwdfc`
transforming planeswalker.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active; none needed. Configured `[dupe_foil] cc2 = []` (2026-11-08) only to enable
`mm query missing-set cc2`.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cc2 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| foil finish (Premium box) | 8 | keep — the "foil" basis is the Premium box; whether you count it is a finish-basis choice, not a rule |

**Totals (local prices, 2026-11-04):** ≈ $58 nonfoil / $94 foil for the 8 cards
(Reanimate 5 and Sol Ring 7 lead).

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- Foil and nonfoil come from DIFFERENT sealed products (Premium vs regular box) —
  owning one box gives you one finish of all 8.
- `cc2` 7 Sol Ring and 8 Command Tower are among dozens of printings of those
  cards; confirm the set code when adding.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cc2 = []` — configured 2026-11-08 (enables `mm query missing-set cc2`).
- `config/families.toml` `[[unobtainable.cc2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cc2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander Collection Black / Black Premium | box set (MTGJSON `sealedProduct` category `box_set`, contents `deck`) | nonfoil vs foil versions of the same 8 cards + token |

**Booster types (for `sealed-value` EV):** none — `scripts/sealed_value.py cc2
--list-boosters` → "no booster data in MTGJSON"; value the box via its deck.
