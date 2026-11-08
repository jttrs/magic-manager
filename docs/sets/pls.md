# `pls` — Planeshift

> Per-family memory doc. Read this before answering set-specific questions about
> `pls` or working on `pls`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `pls`
**Family root type:** `expansion`
**Family released:** 2001-02-05
**Last audit:** 2026-11-06 via `/characterize-set pls` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Invasion-block set, old border, no mythics, no basics.** Three rares have a **foil-only alternate-art** print at `N★` (Ertai, Tahngarth, Skyship Weatherlight). Its only promo is an **Ancient Greek** prerelease foil, which can't be synced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `pls` | expansion | 146 | 2001-02-05 | parent — booster set 1–143 + 3 alt-art `N★` foils (no basics) |
| `ppls` | promo | 1 (0 local) | 2001-02-05 | prerelease Questing Phelddagrif `119` — **Ancient Greek** (`lang = grc`), foil, `datestamped`, ~$46; not synced |

`set:pls+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `pls` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R+M ≈ $162 nonfoil / $3438 foil (Meddling Mage 116 ~$36, Diabolic Intent 42 ~$25 / ~$642 foil, Orim's Chant 11 ~$23 / ~$818 foil, Eladamri's Call 106 ~$12, Forsaken City 139 ~$12) |
| alt-art foils | 3 | `pls` 74★ Tahngarth, Talruum Hero (~$231), 107★ Ertai, the Corrupted (~$190), 133★ Skyship Weatherlight (~$250) — foil-only, rare | `regular` | rare-regular — **different art** from 74 / 107 / 133; ≈ $672 |

**`promo_types`:** none on the `★` prints (they're plain booster foils). `ppls` holds one Ancient Greek prerelease Questing Phelddagrif `119`; `mm set sync ppls` 404s (English-only). No fancy-foil sheet →
configured `[dupe_foil] pls = []` (2026-11-08) to enable `mm query missing-set pls`.

---

## 3–4.

The three alt-art `★` foils (~$190–$250 each) are the set's chase prints. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] pls = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `ppls` promo | 1 (0 local) | **owner's call** — Ancient Greek-only, not syncable |
| alt-art `N★` foils | 3 | keep — unique art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `119` | `ppls` | prerelease (Ancient Greek) | Questing Phelddagrif |
| `N★` | `pls` | booster premium foil (alt art) | Skyship Weatherlight 133★ |

---

## 7. Edge cases & gotchas

- **`★` means alternate art here**, not a same-art foil split (contrast [`7ed`](7ed.md), where `N★` is the same art). The base 74 / 107 / 133 also come in foil with the original art.
- **`ppls` is non-English** (Ancient Greek): nothing local.
- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks (Barrage, Comeback, Domain, Scout), Fat Pack, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] pls = []` — configured 2026-11-08 (enables `mm query missing-set pls`).
- `config/families.toml` `[[unobtainable.pls.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.pls]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py pls --list-boosters` (2026-11-06): `draft` EV ~$9.41, `fat-pack` ~$5.95.
