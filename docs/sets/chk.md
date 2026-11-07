# `chk` — Champions of Kamigawa

> Per-family memory doc. Read this before answering set-specific questions about
> `chk` or working on `chk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `chk`
**Family root type:** `expansion`
**Family released:** 2004-10-01
**Last audit:** 2026-11-06 via `/characterize-set chk` (one-at-a-time run — tier decisions pending owner review).

---

> **First Kamigawa set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). Its promo set holds just one prerelease foil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `chk` | expansion | 307 | 2004-10-01 | parent — booster set 1–306 (basics 287–306) + `160a`/`160b` Brothers Yamazaki |
| `pchk` | promo | 1 | 2004-10-01 | prerelease Ryusei, the Falling Star `185★` (alt art, `datestamped`) |

`set:chk+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 307 | `chk` 1–306 plus `160a`/`160b`; basics 287–306 (130 C incl. basics / 89 U / 88 R) | `regular` | rarity/base sub-selectors — R+M ≈ $527 nonfoil / $3273 foil (Minamo, School at Water's Edge 279 ~$58 / ~$380 foil, Shizo, Death's Storehouse 283 ~$43 / ~$199, Sensei's Divining Top 268 ~$40, Marrow-Gnawer 124 ~$32, Kokusho, the Evening Star 122 ~$29, Dosan the Falling Leaf 205 ~$24) |
| Brothers Yamazaki | 2 | `chk` `160a`, `160b` (uncommon; two arts) | `regular` | both kept — distinct printings, one card |

**`promo_types`:** the prerelease Ryusei `185★` (~$5.42) has its own art. It carries `datestamped`, so `missing.drop_datestamped_with_sibling` drops it from missing-set. No fancy-foil sheet →
proposed `[dupe_foil] chk = []` to enable `mm query missing-set chk`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] chk = []` | 0 | **apply** — empty, enables missing-set |
| `pchk` promos | 1 | **owner's call** — its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `185★` | `pchk` | prerelease (alt art) | Ryusei, the Falling Star |

---

## 7. Edge cases & gotchas

- **Brothers Yamazaki has two printings** (`160a`, `160b`, different art), so the uncommon count is 89, one more than the rares.
- **No mythics**, no token set.
- The legendary lands (Minamo, Shizo, …) carry most of the value.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack` and `tournament`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.chk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.chk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / tournament boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py chk --list-boosters` (2026-11-06): `draft` EV ~$12.52, `tournament` ~$52.25, `fat-pack` ~$3.89.
