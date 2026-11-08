# `ptk` — Portal Three Kingdoms

> Per-family memory doc. Read this before answering set-specific questions about
> `ptk` or working on `ptk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ptk`
**Family root type:** `starter`
**Family released:** 1999-05-01
**Last audit:** 2026-11-06 via `/characterize-set ptk` (one-at-a-time run — tier decisions pending owner review).

---

> **Asia-market beginner set themed on the Romance of the Three Kingdoms**, nonfoil only, short print run — the most expensive per-card set in this run (rares ≈ $7451). 15 basics. Its prerelease Lu Bu exists as **two datestamped prints with the same art** (`pptk` 115a, 115b).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ptk` | starter | 180 | 1999-05-01 | parent — 1–165 + basics 166–180 |
| `pptk` | promo | 2 | 1999-05-01 | prerelease Lu Bu, Master-at-Arms `115a` (dated 1999-04-29, ~$40) and `115b` (1999-07-04, ~$37) — nonfoil, `datestamped`, same art as `ptk` 115 |

`set:ptk+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 165 | `ptk` 1–165 (55 C / 55 U / 55 R) | `regular` | rarity sub-selectors — R ≈ $7451 (Imperial Seal 78 ~$1354, Zodiac Dragon 131 ~$850, Riding the Dilu Horse 144 ~$550, Ravages of War 17 ~$254, Capture of Jingzhou 38 ~$203, Dong Zhou, the Tyrant 109 ~$200); U ≈ $1084, C ≈ $585 |
| basics | 15 | `ptk` 166–180 (~$128 total) | `regular` | basics |
| prerelease | 2 | `pptk` 115a, 115b | `regular` | **same art** — auto-dropped |

**`promo_types`:** `pptk` 115a / 115b carry `prerelease` + `datestamped` and share art with `ptk` 115; both are dropped by `drop_datestamped_with_sibling`. They differ only in the date stamp. No fancy-foil sheet →
configured `[dupe_foil] ptk = []` (2026-11-08) to enable `mm query missing-set ptk`.

---

## 3–4.

Imperial Seal 78 (~$1354) and Zodiac Dragon 131 (~$850). Even commons average ~$8. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ptk = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pptk` prereleases | 2 | none needed — auto-dropped (same art); owner's call if both date stamps are wanted |
| whole family | 182 | keep — a real (if Asia-only) set |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `115a` / `115b` | `pptk` | prerelease (two date stamps) | Lu Bu, Master-at-Arms |

---

## 7. Edge cases & gotchas

- **Two prerelease prints of one card** (115a dated 1999-04-29, 115b dated 1999-07-04): a date-stamp variant, not an art variant.
- **No foils at all**, including the promos.
- **Basics are ~$8 each.**
- MTGJSON: Two Player Starter (decks `Preconstructed deck 1`/`2`, typed `Starter Deck`), 3 Theme Decks (Shu, Wei, Wu Kingdom). Boosters: `sealed-value` lists a `default` booster.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ptk = []` — configured 2026-11-08 (enables `mm query missing-set ptk`).
- `config/families.toml` `[[unobtainable.ptk.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ptk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Two Player Starter | starter set | two decks |
| Theme Decks ×3 | theme deck | Shu / Wei / Wu |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ptk --list-boosters` (2026-11-06): `default` EV ~$233.47.
