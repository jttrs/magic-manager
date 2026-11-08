# `lgn` — Legions

> Per-family memory doc. Read this before answering set-specific questions about
> `lgn` or working on `lgn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `lgn`
**Family root type:** `expansion`
**Family released:** 2003-02-03
**Last audit:** 2026-11-06 via `/characterize-set lgn` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Onslaught set, all creatures, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). Before 2003-10 the prerelease foil has a **plain CN** (no `★`) and **reuses the booster art**. No basics.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `lgn` | expansion | 145 | 2003-02-03 | parent — booster set 1–145 (no basics) |
| `plgn` | promo | 1 | 2003-02-03 | prerelease Feral Throwback `126` (same art, `datestamped`) |

`set:lgn+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 145 | `lgn` 1–145, no basic lands (55 C / 45 U / 45 R) | `regular` | rarity/base sub-selectors — R+M ≈ $183 nonfoil / $2128 foil (Seedborn Muse 138 ~$32 / ~$363 foil, Akroma, Angel of Wrath 1 ~$21 / ~$400, Caller of the Claw 121 ~$19, Graveborn Muse 73 ~$19 / ~$325, Phage the Untouchable 78 ~$13 / ~$197) |

**`promo_types`:** the prerelease Feral Throwback `126` (~$0.94) reuses the booster art, on the same CN. It carries `datestamped`, so missing-set drops it — a same-art foil. No fancy-foil sheet →
proposed `[dupe_foil] lgn = []` to enable `mm query missing-set lgn`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] lgn = []` | 0 | **apply** — empty, enables missing-set |
| `plgn` promos | 1 | **owner's call** — same art as the booster card |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `126` | `plgn` | prerelease (same art) | Feral Throwback |

---

## 7. Edge cases & gotchas

- **Every card is a creature** (no spells); no basic lands, no mythics, no token set.
- **Promo CN equals the booster CN.**
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.lgn.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.lgn]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py lgn --list-boosters` (2026-11-06): `draft` EV ~$10.64, `fat-pack` ~$9.68.
