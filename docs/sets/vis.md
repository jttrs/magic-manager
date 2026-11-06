# `vis` — Visions

> Per-family memory doc. Read this before answering set-specific questions about
> `vis` or working on `vis`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `vis`
**Family root type:** `expansion`
**Family released:** 1997-02-03
**Last audit:** 2026-11-06 via `/characterize-set vis` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Mirage-block set, old border, nonfoil only, no basics.** Its child `mgb` (Multiverse Gift Box) holds 10 Visions rares with the same art, unpriced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `vis` | expansion | 167 | 1997-02-03 | parent — booster set 1–167 (no basics) |
| `mgb` | box | 10 | 1996-11-01 | Multiverse Gift Box — 10 Visions rares, same art as `vis`, nonfoil, unpriced |

`set:vis+related` covers both. `mgb` is released three months **before** its parent.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 167 | `vis` 1–167 (62 C / 55 U / 50 R) | `regular` | rarity/base sub-selectors — R ≈ $464 (Squandered Resources 137 ~$84, Vampiric Tutor 72 ~$75, Anvil of Bogardan 141 ~$47, Natural Order 114 ~$39, Tithe 23 ~$37, Undiscovered Paradise 167 ~$35) |
| Multiverse Gift Box | 10 | `mgb` 1–10 (rare: Peace Talks, Ovinomancer, Dark Privilege, Necrosavant, Urborg Mindsucker, Vampirism, Wicked Reward, Viashino Sandstalker, Bull Elephant, King Cheetah) | `regular` | rare-regular — **same art** as `vis`; no dupe signal, so missing-set lists them |

**`promo_types`:** none. The `mgb` prints carry no `promo_types`, so nothing marks them as dupes of the `vis` rares. No fancy-foil sheet →
proposed `[dupe_foil] vis = []` to enable `mm query missing-set vis`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] vis = []` | 0 | **apply** — empty, enables missing-set |
| `mgb` gift-box rares | 10 | **owner's call** — same-art early printings of `vis` rares, unpriced; exclude (`set_code` rule) unless you track the gift box |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `1`–`10` | `mgb` | Multiverse Gift Box | Peace Talks 1 |

---

## 7. Edge cases & gotchas

- **`mgb` duplicates 10 `vis` rares with no marker** — same art, own set code, no price. A missing-set run lists them as 10 extra rares.
- **No foils.**
- MTGJSON: decks typed `MTGO Theme Deck` (Legion of Glory, Savage Stompdown, Unnatural Forces, Wild-Eyed Frenzy); sealed *Multiverse Gift Box* (`bundle` / `gift_bundle`). Boosters include a `preview` type.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.vis.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.vis]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Multiverse Gift Box | gift bundle | the 10 `mgb` rares |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py vis --list-boosters` (2026-11-06): `draft` EV ~$16.39, `preview` ~$14.37.
