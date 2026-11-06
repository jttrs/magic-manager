# `ice` — Ice Age

> Per-family memory doc. Read this before answering set-specific questions about
> `ice` or working on `ice`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ice`
**Family root type:** `expansion`
**Family released:** 1995-06-03
**Last audit:** 2026-11-06 via `/characterize-set ice` (one-at-a-time run — tier decisions pending owner review).

---

> **First Ice Age-block set, old border, nonfoil only.** 20 basics. No promo or token set. Home of the original painlands (351–362).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ice` | expansion | 383 | 1995-06-03 | parent — booster set 1–363 + basics 364–383 |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 383 | `ice` 1–383 (121 C / 121 U / 121 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $397 (Necropotence 154 ~$47, Underground River 362 ~$29, Karplusan Forest 356 ~$28, Adarkar Wastes 351 ~$24, Sulfurous Springs 360 ~$20, Brushland 352 ~$17) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] ice = []` to enable `mm query missing-set ice`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ice = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **The painlands** (Adarkar Wastes, Brushland, Karplusan Forest, Sulfurous Springs, Underground River) are nearly a third of rare value (~$118).
- **No foils.**
- MTGJSON: Ice Age Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ice.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ice]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ice --list-boosters` (2026-11-06): `default` EV ~$12.49, `starter` ~$62.82.
