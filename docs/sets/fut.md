# `fut` — Future Sight

> Per-family memory doc. Read this before answering set-specific questions about
> `fut` or working on `fut`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `fut`
**Family root type:** `expansion`
**Family released:** 2007-05-04
**Last audit:** 2026-11-06 via `/characterize-set fut` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Time Spiral set, pre-mythic, with "futureshifted" cards in a future frame.** Old border-era rarity: **no mythics** (C/U/R). The futureshifted frame isn't flagged locally (no `frame_effects`), so they're plain base cards.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `fut` | expansion | 180 | 2007-05-04 | parent — booster set 1–180 (no basics) |
| `pfut` | promo | 2 | 2007-05-04 | prerelease Korlash, Heir to Blackblade `87★` (alt art, `datestamped`, ~$19) + release Storm Entity `122★` (same art) |

`set:fut+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 180 | `fut` 1–180, no basic lands (60 C / 60 U / 60 R) | `regular` | rarity/base sub-selectors — R+M ≈ $307 nonfoil / $2193 foil (Sliver Legion 158 ~$51 / ~$240 foil, Akroma's Memorial 159 ~$37, Bitter Ordeal 80 ~$28, Tarmogoyf 153 ~$26 / ~$188 foil, Pact of Negation 42 ~$21 / ~$188 foil) |

**`promo_types`:** the prerelease Korlash `87★` has its own art; the release Storm Entity `122★` (~$1.32) reuses the booster art. Only the prerelease carries `datestamped` (dropped by missing-set); the same-art release foil is listed next to `fut` 122. No fancy-foil sheet →
configured `[dupe_foil] fut = []` (2026-11-08) to enable `mm query missing-set fut`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] fut = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pfut` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `87★` | `pfut` | prerelease (alt art) | Korlash, Heir to Blackblade |
| `122★` | `pfut` | release (same art) | Storm Entity |

---

## 7. Edge cases & gotchas

- **Five `full_art = 1` prints** (Blade of the Sixth Pride 19, Blind Phantasm 49 — also `inverted` —, Mass of Ghouls 88, Fomori Nomad 114, Nessian Courser 148): Scryfall's flag for the textless-vanilla future-frame commons, not a treatment the selectors care about.
- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks + MTGO Redemption (not in `PRECON_MODERN_TYPES`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] fut = []` — configured 2026-11-08 (enables `mm query missing-set fut`).
- `config/families.toml` `[[unobtainable.fut.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.fut]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py fut --list-boosters` (2026-11-06): `draft` EV ~$13.25.
