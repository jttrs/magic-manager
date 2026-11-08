# `mrd` — Mirrodin

> Per-family memory doc. Read this before answering set-specific questions about
> `mrd` or working on `mrd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mrd`
**Family root type:** `expansion`
**Family released:** 2003-10-02
**Last audit:** 2026-11-06 via `/characterize-set mrd` (one-at-a-time run — tier decisions pending owner review).

---

> **First Mirrodin set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). Artifact lands at common. The prerelease foil is Sword of Kaldra (Kaldra cycle: Shield `pdst`, Helm `p5dn`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mrd` | expansion | 306 | 2003-10-02 | parent — booster set 1–306 (basics 287–306) |
| `pmrd` | promo | 1 | 2003-10-02 | prerelease Sword of Kaldra `251★` (alt art, `datestamped`, ~$33) |

`set:mrd+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 306 | `mrd` 1–306; basics 287–306 (130 C incl. basics / 88 U / 88 R) | `regular` | rarity/base sub-selectors — R+M ≈ $477 nonfoil / $1966 foil (Chrome Mox 152 ~$167 / ~$449 foil, Quicksilver Elemental 47 ~$20, Sword of Kaldra 251 ~$18, Krark's Thumb 190 ~$18, Chalice of the Void 150 ~$17, Mesmeric Orb 204 ~$17) |

**`promo_types`:** the prerelease Sword of Kaldra `251★` (~$32.74) has its own art. It carries `datestamped`, so missing-set drops it (a ~$33 alt-art card hidden). No fancy-foil sheet →
configured `[dupe_foil] mrd = []` (2026-11-08) to enable `mm query missing-set mrd`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mrd = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pmrd` promos | 1 | **owner's call** — its own art (~$33) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `251★` | `pmrd` | prerelease (alt art) | Sword of Kaldra |

---

## 7. Edge cases & gotchas

- **No mythics**, no token set.
- Chrome Mox 152 is a third of the rare value.
- Commons are worth more than usual (≈ $65 nonfoil / $752 foil — the artifact lands).
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack` and `tournament`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] mrd = []` — configured 2026-11-08 (enables `mm query missing-set mrd`).
- `config/families.toml` `[[unobtainable.mrd.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.mrd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft / tournament boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mrd --list-boosters` (2026-11-06): `draft` EV ~$15.07, `tournament` ~$54.84, `fat-pack` ~$7.62.
