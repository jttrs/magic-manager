# `ren` — Renaissance

> Per-family memory doc. Read this before answering set-specific questions about
> `ren` or working on `ren`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ren`
**Family root type:** `masters`
**Family released:** 1995-08-01
**Last audit:** 2026-11-06 via `/characterize-set ren` (one-at-a-time run — tier decisions pending owner review).

---

> **French and German Renaissance** — 122 reprints, each printed in both languages (244 prints, `lang = fr` / `de`). Nothing local: `mm set sync` asks for English only.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ren` | masters | 122 (0 local; 244 prints on Scryfall) | 1995-08-01 | parent — French + German reprints |

No children. With no English prints, `mm set master-list ren` finds nothing to list.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| French / German reprints | 244 (0 local) | `ren` (e.g. Abomination 46, Alabaster Potion 2) | — | not syncable |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] ren = []` to enable `mm query missing-set ren`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ren = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 244 (0 local) | **owner's call** — non-English only; can't be synced |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Non-English-only set:** each card has a French and a German print with the same CN. A `lang:any` sync would need a language key in the local schema to tell them apart.
- Sibling of [`rin`](rin.md) (Italian) and [`chr`](chr.md) (the English Chronicles).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ren.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ren]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | French / German |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ren --list-boosters` (2026-11-06): none listed locally (`default` EV $0.00 — no local prices).
