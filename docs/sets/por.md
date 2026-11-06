# `por` — Portal

> Per-family memory doc. Read this before answering set-specific questions about
> `por` or working on `por`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `por`
**Family root type:** `starter`
**Family released:** 1997-05-01
**Last audit:** 2026-11-06 via `/characterize-set por` (one-at-a-time run — tier decisions pending owner review).

---

> **First Portal beginner set, nonfoil only, no promos or tokens.** 20 basics. **29 Simplified-Chinese alt-art prints** (`Ns`, `lang = zhs`) are on Scryfall but not local — some are priced at $95–$150.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `por` | starter | 215 (244 English+`zhs` on Scryfall) | 1997-05-01 | parent — 1–195 + basics 196–215 |

No children. `starter` isn't a default inventory set type, but the anchor is always included by `mm set master-list por`. The 29 Scryfall-only rows are `schinesealtart` prints (`lang = zhs`), e.g. Elven Cache 164s (~$150), Forest 213s (~$150), Vampiric Feast 114s (~$100), 16 basics, and a second Blaze `118†s`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards | 195 | `por` 1–195 (85 C / 55 U / 55 R) | `regular` | rarity sub-selectors — R ≈ $511 (Wrath of God 39 ~$71, Sylvan Tutor 188 ~$65, Cruel Tutor 87 ~$47, Armageddon 5 ~$36, Natural Order 175 ~$27, Harsh Justice 18 ~$23) |
| basics | 20 | `por` 196–215 | `regular` | basics |

**`promo_types`:** none locally. The `schinesealtart` prints are Chinese-language only. No fancy-foil sheet →
proposed `[dupe_foil] por = []` to enable `mm query missing-set por`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] por = []` | 0 | **apply** — empty, enables missing-set |
| `zhs` alt-art `Ns` | 29 (0 local) | **owner's call** — Chinese-only, not syncable; several cost more than the set's top rare |
| whole family | 215 | **owner's call** — a beginner set with real boosters; kept (default) — pending owner review |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `N†s` | `por` | Simplified-Chinese alt art (`schinesealtart`) | Elven Cache 164s |

---

## 7. Edge cases & gotchas

- **The Chinese alt-art run is large here** (29 prints, incl. most basics), the biggest of the `schinesealtart` sets characterized so far ([`5ed`](5ed.md), [`6ed`](6ed.md), [`usg`](usg.md), [`7ed`](7ed.md), [`inv`](inv.md)).
- **No foils.**
- MTGJSON: Two Player Starter Set (decks `Preconstructed deck 1`/`2`), Gift Box, 2 Demo Decks.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.por.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.por]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Two Player Starter Set | starter set | two decks |
| Gift Box | gift bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py por --list-boosters` (2026-11-06): `default` EV ~$19.84.
