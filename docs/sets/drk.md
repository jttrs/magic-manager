# `drk` — The Dark

> Per-family memory doc. Read this before answering set-specific questions about
> `drk` or working on `drk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `drk`
**Family root type:** `expansion`
**Family released:** 1994-08-01
**Last audit:** 2026-11-06 via `/characterize-set drk` (one-at-a-time run — tier decisions pending owner review).

---

> **Old-border expansion, nonfoil only, no basics, no promos.** 119 cards, one art each.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `drk` | expansion | 119 | 1994-08-01 | parent — CN 1–119 |

No children. (`mm set list-related` reports 122; Scryfall's English search returns 119.)

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 119 | `drk` 1–119 (40 C / 44 U / 35 R) | `regular` | rarity/base sub-selectors — R ≈ $539 (Goblin Wizard 69 ~$96, City of Shadows 116 ~$71, Blood Moon 58 ~$69, Ball Lightning 57 ~$50); U ≈ $174 (Maze of Ith 117 ~$36, Tormod's Crypt 112 ~$31, Elves of Deep Shadow 76 ~$21) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] drk = []` to enable `mm query missing-set drk`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] drk = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Valuable uncommons** (Maze of Ith, Tormod's Crypt, Elves of Deep Shadow; U ≈ a quarter of the set's value) are invisible to the rare/mythic sub-selectors.
- **No foils.** MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.drk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.drk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py drk --list-boosters` (2026-11-06): `default` EV ~$19.48.
