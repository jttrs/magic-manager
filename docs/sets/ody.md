# `ody` — Odyssey

> Per-family memory doc. Read this before answering set-specific questions about
> `ody` or working on `ody`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ody`
**Family root type:** `expansion`
**Family released:** 2001-10-01
**Last audit:** 2026-11-06 via `/characterize-set ody` (one-at-a-time run — tier decisions pending owner review).

---

> **First Odyssey-block set, old border, no mythics (C/U/R).** Flashback cards carry `tombstone`. 20 basics. Its only promo is an **Arabic** prerelease foil, which can't be synced.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ody` | expansion | 350 | 2001-10-01 | parent — booster set 1–330, basics 331–350 |
| `pody` | promo | 1 (0 local) | 2001-10-01 | prerelease Stone-Tongue Basilisk `276` — **Arabic** (`lang = ar`), foil, `datestamped`, ~$41; not synced (English-only sync) |

`set:ody+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `ody` 1–350 (130 C / 110 U / 110 R; basics 331–350) | `regular` | rarity/base sub-selectors — R+M ≈ $440 nonfoil / $5090 foil (Tainted Pact 164 ~$42 / ~$510 foil, Terravore 278 ~$27, Entomb 132 ~$24 / ~$520 foil, Call of the Herd 231 ~$22, Tarnished Citadel 329 ~$20) |
| tombstone (flashback) | 28 | `ody` (13 C / 11 U / 4 R) | `regular` | part of base — cosmetic |

**`promo_types`:** `pody` holds one Arabic prerelease Stone-Tongue Basilisk `276`. `mm set sync pody` 404s (it asks for `lang:en`), so the promo is absent locally. No fancy-foil sheet →
proposed `[dupe_foil] ody = []` to enable `mm query missing-set ody`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ody = []` | 0 | **apply** — empty, enables missing-set |
| `pody` promo | 1 (0 local) | **owner's call** — Arabic-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `276` | `pody` | prerelease (Arabic) | Stone-Tongue Basilisk |

---

## 7. Edge cases & gotchas

- **`pody` is non-English** (Arabic): nothing local. The 2001–2002 prerelease promos were each printed in one unusual language (see [`apc`](apc.md), [`pls`](pls.md), [`tor`](tor.md)).
- **No mythics.** Foil prices dwarf nonfoil (R foil total ~11× nonfoil).
- MTGJSON: 4 Theme Decks (Liftoff, One Two Punch, Pressure Cooker, Trounce O Matic), Tournament Pack, Fat Pack, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ody.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ody]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Tournament Pack | starter-size sealed pack (`limited_aid_tool` / `tournament_deck`) | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ody --list-boosters` (2026-11-06): `draft` EV ~$11.38, `fat-pack` ~$13.71, `tournament` ~$62.79.
