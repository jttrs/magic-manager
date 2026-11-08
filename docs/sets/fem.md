# `fem` — Fallen Empires

> Per-family memory doc. Read this before answering set-specific questions about
> `fem` or working on `fem`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `fem`
**Family root type:** `expansion`
**Family released:** 1994-11-01
**Last audit:** 2026-11-06 via `/characterize-set fem` (one-at-a-time run — tier decisions pending owner review).

---

> **Old-border expansion, nonfoil only, no basics, no promos.** **35 commons come in 2–4 arts** (`Na`–`Nd`), so 102 cards are 187 prints. Low value.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `fem` | expansion | 187 | 1994-11-01 | parent — CN 1–102; 35 commons split into `Na`…`Nd` |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| single-art cards | 67 | `fem` (36 R / 30 U / 1 C) | `regular` | rarity/base sub-selectors — R ≈ $52 (Rainbow Vale 99 ~$6, Hand of Justice 5 ~$6, Dwarven Armorer 50 ~$5, Conch Horn 83 ~$4) |
| multi-art commons | 120 | `fem` `Na`–`Nd` for 35 names (15 names in 4 arts, e.g. Hymn to Tourach 38a–38d) | `regular` | commons — **different art** per letter |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] fem = []` (2026-11-08) to enable `mm query missing-set fem`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] fem = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **`a`–`d` CNs are separate arts**; 15 commons have four (Armor Thrull, Basal Thrull, Brassclaw Orcs, Combat Medic, Elven Fortress, Goblin War Drums, Homarid, Hymn to Tourach, Icatian Infantry, Icatian Scout, Merseine, Orcish Veteran, Thallid, Thorn Thallid, Vodalian Soldiers).
- **No basics, no foils.** MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] fem = []` — configured 2026-11-08 (enables `mm query missing-set fem`).
- `config/families.toml` `[[unobtainable.fem.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.fem]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py fem --list-boosters` (2026-11-06): `default` EV ~$3.03.
