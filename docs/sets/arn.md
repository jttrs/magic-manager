# `arn` — Arabian Nights

> Per-family memory doc. Read this before answering set-specific questions about
> `arn` or working on `arn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `arn`
**Family root type:** `expansion`
**Family released:** 1993-12-17
**Last audit:** 2026-11-06 via `/characterize-set arn` (one-at-a-time run — tier decisions pending owner review).

---

> **First Magic expansion, old border, nonfoil only.** 78 cards, one basic (Mountain 77). **14 English `N†` variation prints** (the dark/light mana-symbol printings, same art) are on Scryfall but not local.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `arn` | expansion | 78 (92 on Scryfall) | 1993-12-17 | parent — CN 1–78 |

No children. The 14 Scryfall-only rows are `variation` prints with the same art as their base CN: Army of Allah 2† (~$36), Wyluli Wolf 55† (~$36), Rukh Egg 43† (~$46), Oubliette 31† (~$24), War Elephant 11† (~$18), Piety 8†, Giant Tortoise 15†, Bird Maiden 37†, Fishliver Oil 13†, Moorish Cavalry 7†, Erg Raiders 25†, Nafs Asp 52†, Hasran Ogress 27†, Stone-Throwing Devils 33†. Scryfall's search hides variations, so `mm set sync` never fetches them.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 78 | `arn` 1–78 (26 C / 18 U / 33 R + Mountain 77) | `regular` | rarity/base sub-selectors — R ≈ $8940 (Juzám Djinn 29 ~$2114, Diamond Valley 73 ~$690, Guardian Beast 26 ~$625, Drop of Honey 47 ~$608, Serendib Efreet 20 ~$580); U ≈ $5472 (Bazaar of Baghdad 70 ~$2013, Library of Alexandria 76 ~$1940, City of Brass 71 ~$802); C ≈ $554 |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] arn = []` (2026-11-08) to enable `mm query missing-set arn`.

---

## 3–4.

Juzám Djinn 29, Bazaar of Baghdad 70, Library of Alexandria 76 (each ~$1950–2110). No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] arn = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `variation` `N†` | 14 (0 local) | **owner's call** — same-art English printing variants (~$290 total); invisible until sync fetches variations |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N†` | `arn` | mana-symbol variation (not synced) | Rukh Egg 43† |

---

## 7. Edge cases & gotchas

- **Two of the three priciest cards are uncommons** (Bazaar of Baghdad, Library of Alexandria): uncommons are ~37% of the set's value.
- **Variation prints are never synced** (see family map).
- **One basic land** (Mountain 77).
- MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] arn = []` — configured 2026-11-08 (enables `mm query missing-set arn`).
- `config/families.toml` `[[unobtainable.arn.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.arn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py arn --list-boosters` (2026-11-06): `default` EV ~$634.66.
