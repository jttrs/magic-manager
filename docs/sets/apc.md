# `apc` — Apocalypse

> Per-family memory doc. Read this before answering set-specific questions about
> `apc` or working on `apc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `apc`
**Family root type:** `expansion`
**Family released:** 2001-06-04
**Last audit:** 2026-11-06 via `/characterize-set apc` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Invasion-block set, old border, no mythics, no basics.** Home of the five enemy painlands (CN 139–143). Its only promo is a **Sanskrit** prerelease foil, which can't be synced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `apc` | expansion | 143 | 2001-06-04 | parent — booster set 1–143 (no basics) |
| `papc` | promo | 1 (0 local) | 2001-06-04 | prerelease Fungal Shambler `100` — **Sanskrit** (`lang = sa`), foil, `datestamped`, ~$15; not synced |

`set:apc+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `apc` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R+M ≈ $197 nonfoil / $2871 foil (Llanowar Wastes 141 ~$29, Yavimaya Coast 143 ~$28, Shivan Reef 142 ~$26, Phyrexian Arena 47 ~$19, Pernicious Deed 114 ~$17) |
| enemy painlands | 5 | `apc` 139–143 (Battlefield Forge, Caves of Koilos, Llanowar Wastes, Shivan Reef, Yavimaya Coast; rare) | `regular` | part of base — about half the rare value |

**`promo_types`:** `papc` holds one Sanskrit prerelease Fungal Shambler `100`. `mm set sync papc` 404s (English-only), so it's absent locally. No fancy-foil sheet →
configured `[dupe_foil] apc = []` (2026-11-08) to enable `mm query missing-set apc`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] apc = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `papc` promo | 1 (0 local) | **owner's call** — Sanskrit-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `100` | `papc` | prerelease (Sanskrit) | Fungal Shambler |

---

## 7. Edge cases & gotchas

- **`papc` is non-English** (Sanskrit): nothing local.
- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks (Burial, Pandemonium, Swoop, Whirlpool), Fat Pack, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] apc = []` — configured 2026-11-08 (enables `mm query missing-set apc`).
- `config/families.toml` `[[unobtainable.apc.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.apc]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py apc --list-boosters` (2026-11-06): `draft` EV ~$8.74, `fat-pack` ~$3.59.
