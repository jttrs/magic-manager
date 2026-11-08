# `sth` — Stronghold

> Per-family memory doc. Read this before answering set-specific questions about
> `sth` or working on `sth`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `sth`
**Family root type:** `expansion`
**Family released:** 1998-03-02
**Last audit:** 2026-11-06 via `/characterize-set sth` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Tempest-block set, old border, nonfoil only, no basics, no mythics.** Home of Mox Diamond. Its prerelease promo (`psth` Revenant 68) is nonfoil, same CN and art as the booster card.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `sth` | expansion | 143 | 1998-03-02 | parent — booster set 1–143 (no basics) |
| `psth` | promo | 1 | 1998-03-02 | prerelease Revenant `68` — nonfoil, `datestamped`, same art as `sth` 68, ~$6 |

`set:sth+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `sth` 1–143 (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R ≈ $1802 (Mox Diamond 138 ~$1120, Sliver Queen 129 ~$302, Volrath's Stronghold 143 ~$140, Burgeoning 102 ~$36, Dream Halls 28 ~$33, Grave Pact 60 ~$32) |
| prerelease | 1 | `psth` 68 | `regular` | **same art** — auto-dropped |

**`promo_types`:** `psth` 68 carries `prerelease` + `datestamped` and shares art with `sth` 68, so missing-set drops it correctly. No fancy-foil sheet →
configured `[dupe_foil] sth = []` (2026-11-08) to enable `mm query missing-set sth`.

---

## 3–4.

Mox Diamond 138 (~$1120) is ~62% of rare value. No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] sth = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `psth` prerelease | 1 | none needed — auto-dropped (same art) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `68` | `psth` | prerelease (nonfoil, datestamped, same art) | Revenant |

---

## 7. Edge cases & gotchas

- **Pre-foil era:** every print is nonfoil.
- MTGJSON: 4 Theme Decks (Call of the Kor, Migraine, The Sparkler, The Spikes) plus an `Advanced Deck` version of each.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] sth = []` — configured 2026-11-08 (enables `mm query missing-set sth`).
- `config/families.toml` `[[unobtainable.sth.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.sth]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 (+ Advanced) | theme deck | not in `PRECON_MODERN_TYPES` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py sth --list-boosters` (2026-11-06): `draft` EV ~$48.24.
