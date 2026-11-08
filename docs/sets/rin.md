# `rin` — Rinascimento

> Per-family memory doc. Read this before answering set-specific questions about
> `rin` or working on `rin`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rin`
**Family root type:** `masters`
**Family released:** 1995-08-01
**Last audit:** 2026-11-06 via `/characterize-set rin` (one-at-a-time run — tier decisions pending owner review).

---

> **Italian-only Renaissance** — 69 reprints (`lang = it`). Nothing local: `mm set sync` asks Scryfall for English cards only.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rin` | masters | 69 (0 local) | 1995-08-01 | parent — Italian-only reprints |

No children. `masters` isn't a default inventory set type, and the set has no English prints, so `mm set master-list rin` finds nothing to list.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Italian reprints | 69 (0 local) | `rin` 1–… (e.g. Abu Ja'far 1 ~$1.59, Aladdin 70 ~$10) | — | not syncable |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] rin = []` (2026-11-08) to enable `mm query missing-set rin`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] rin = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 69 (0 local) | **owner's call** — Italian-only; can't be synced (same gap as [`ps11`](ps11.md), [`psal`](psal.md)) |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Non-English-only set:** `mm set sync rin` returns nothing, so every command sees an empty set. Fixing this needs a code change (sync with `lang:any` for such sets).
- Sibling of [`ren`](ren.md) (French + German).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] rin = []` — configured 2026-11-08 (enables `mm query missing-set rin`).
- `config/families.toml` `[[unobtainable.rin.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.rin]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | Italian |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rin --list-boosters` (2026-11-06): none listed locally (`default` EV $0.00 — no local prices).
