# `eve` — Eventide

> Per-family memory doc. Read this before answering set-specific questions about
> `eve` or working on `eve`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `eve`
**Family root type:** `expansion`
**Family released:** 2008-07-25
**Last audit:** 2026-11-05 via `/characterize-set eve` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Shadowmoor set — enemy-colour hybrid.** **No mythics.** Two promos: an alt-art prerelease foil and a same-art release foil.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `eve` | expansion | 180 | 2008-07-25 | parent — booster set 1–180 (no basics) |
| `peve` | promo | 2 | 2008-07-25 | prerelease Overbeing of Myth `157★` (alt art, `datestamped`) + release Figure of Destiny `139★` (same art) |
| `teve` | token | 7 | 2008-07-25 | tokens |

`set:eve+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 180 | `eve` 1–180 (60 C / 60 U / 60 R) | `regular` | rarity/base sub-selectors — R+M ≈ $268 nonfoil / $1349 foil (Ward of Bones 174 ~$29, Ashling, the Extinguisher 33 ~$25, Crumbling Ashes 35 ~$24, Bloom Tender 66 ~$19 / **$185** foil, Waves of Aggression 148) |

**`promo_types`:** the prerelease Overbeing `157★` has its own art; the release Figure of Destiny `139★` reuses the booster art. The prerelease is `datestamped` (dropped by `missing.drop_datestamped_with_sibling`); the release foil isn't, so missing-set lists it. No fancy-foil sheet →
configured `[dupe_foil] eve = []` (2026-11-08) to enable `mm query missing-set eve`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] eve = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `peve` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `157★` | `peve` | prerelease (alt art) | Overbeing of Myth |
| `139★` | `peve` | release (same art) | Figure of Destiny |

---

## 7. Edge cases & gotchas

- **No mythics, no basics** (boosters used [`shm`](shm.md) basics).
- **Equal rarity counts** (60 / 60 / 60).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] eve = []` — configured 2026-11-08 (enables `mm query missing-set eve`).
- `config/families.toml` `[[unobtainable.eve.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.eve]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×5 | theme deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py eve --list-boosters` (2026-11-05): `draft` EV ~$11.85.
