# `jud` — Judgment

> Per-family memory doc. Read this before answering set-specific questions about
> `jud` or working on `jud`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `jud`
**Family root type:** `expansion`
**Family released:** 2002-05-27
**Last audit:** 2026-11-06 via `/characterize-set jud` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Odyssey set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Flashback cards carry the `tombstone` frame effect (cosmetic). Its only promo is a **Hebrew** prerelease foil, which can't be synced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `jud` | expansion | 143 | 2002-05-27 | parent — booster set 1–143 (no basics) |
| `pjud` | promo | 1 (0 local) | 2002-05-27 | prerelease Glory `11` — **Hebrew** (`lang = he`), foil, `datestamped`, ~$36; not synced (English-only sync) |

`set:jud+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `jud` 1–143, no basic lands (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R+M ≈ $182 nonfoil / $2228 foil (Cabal Therapy 62 ~$19 / ~$258 foil, Sylvan Safekeeper 133 ~$15 / ~$359, Seedtime 130 ~$13, Balthor the Defiled 61 ~$12, Dwarven Bloodboiler 84 ~$10 / ~$166) |
| tombstone (flashback) | 23 | `jud` (7 C / 12 U / 4 R; e.g. Cabal Therapy 62, Glory 11, Genesis 117) | `regular` | part of base — `tombstone` is cosmetic |

**`promo_types`:** `pjud` holds one Hebrew prerelease Glory `11`. `mm set sync pjud` 404s (it asks for `lang:en`), so the family's promo is absent locally. No fancy-foil sheet →
configured `[dupe_foil] jud = []` (2026-11-08) to enable `mm query missing-set jud`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] jud = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pjud` promos | 1 (0 local) | **owner's call** — Hebrew-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `11` | `pjud` | prerelease (Hebrew) | Glory |

---

## 7. Edge cases & gotchas

- **`pjud` is non-English** (Hebrew), like `ps11`/`psal`: nothing local, so missing-set can't see it.
- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] jud = []` — configured 2026-11-08 (enables `mm query missing-set jud`).
- `config/families.toml` `[[unobtainable.jud.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.jud]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py jud --list-boosters` (2026-11-06): `draft` EV ~$18.64, `fat-pack` ~$9.08.
