# `hml` — Homelands

> Per-family memory doc. Read this before answering set-specific questions about
> `hml` or working on `hml`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `hml`
**Family root type:** `expansion`
**Family released:** 1995-10-01
**Last audit:** 2026-11-06 via `/characterize-set hml` (one-at-a-time run — tier decisions pending owner review).

---

> **Standalone expansion, old border, nonfoil only, no basics, no promos.** **25 commons come in two arts** (`Na` / `Nb`), so 115 cards are 140 prints. The lowest-value booster in this run.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `hml` | expansion | 140 | 1995-10-01 | parent — CN 1–115; 25 commons split into `Na` / `Nb` |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| single-art cards | 90 | `hml` (21 C / 27 U / 42 R) | `regular` | rarity/base sub-selectors — R ≈ $96 (Didgeridoo 105 ~$21, Koskun Falls 55 ~$17, Willow Priestess 100 ~$7, Merchant Scroll 33 ~$6 (common), Baron Sengir 41 ~$5) |
| two-art commons | 50 | `hml` `Na` / `Nb` for 25 names (all common) | `regular` | commons — **different art** per letter |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] hml = []` to enable `mm query missing-set hml`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] hml = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **`a`/`b` CNs are separate arts** (Abbey Matron 2a / 2b, Aliban's Tower 61a / 61b, …).
- **No basics, no foils.**
- MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.hml.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.hml]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py hml --list-boosters` (2026-11-06): `default` EV ~$3.20.
