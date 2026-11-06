# `tor` — Torment

> Per-family memory doc. Read this before answering set-specific questions about
> `tor` or working on `tor`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tor`
**Family root type:** `expansion`
**Family released:** 2002-02-04
**Last audit:** 2026-11-06 via `/characterize-set tor` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Odyssey set (black-heavy), pre-mythic.** Old border-era rarity: **no mythics** (C/U/R), no basics. Flashback cards carry `tombstone`. Its only promo is a **Russian** prerelease foil, which can't be synced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tor` | expansion | 143 | 2002-02-04 | parent — booster set 1–143 (no basics) |
| `ptor` | promo | 1 (0 local) | 2002-02-04 | prerelease Laquatus's Champion `67` — **Russian** (`lang = ru`), foil, `datestamped`, ~$15; not synced (English-only sync) |

`set:tor+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 143 | `tor` 1–143, no basic lands (55 C / 44 U / 44 R) | `regular` | rarity/base sub-selectors — R+M ≈ $143 nonfoil / $1382 foil (Cabal Coffers 139 ~$29 / ~$220 foil, Grim Lavamancer 100 ~$20 / ~$226, Cabal Ritual 51 ~$20 / ~$225, Insidious Dreams 66 ~$17, Nantuko Shade 74 ~$17) |
| tombstone (flashback) | 10 | `tor` (5 C / 2 U / 3 R) | `regular` | part of base — cosmetic |

**`promo_types`:** `ptor` holds one Russian prerelease Laquatus's Champion `67`. `mm set sync ptor` 404s (it asks for `lang:en`), so the promo is absent locally. (`mm set list-related` reports `ptor` as 3 cards: the other 2 are Russian variation prints, see §7.) No fancy-foil sheet →
proposed `[dupe_foil] tor = []` to enable `mm query missing-set tor`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] tor = []` | 0 | **apply** — empty, enables missing-set |
| `ptor` promos | 1 (0 local) | **owner's call** — Russian-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `67` | `ptor` | prerelease (Russian) | Laquatus's Champion |

---

## 7. Edge cases & gotchas

- **`ptor` also has two Russian variation prints** (`67†`, `67†a`) — the other 2 in `mm set list-related`'s count. Scryfall's search leaves out `variation` prints, so `mm set sync` never fetches them, and they're non-English anyway.
- **`ptor` is non-English** (Russian): nothing local.
- **No basic lands**, **no mythics**, no token set.
- MTGJSON: 4 Theme Decks + MTGO Redemption; boosters include `fat-pack`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.tor.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.tor]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py tor --list-boosters` (2026-11-06): `draft` EV ~$17.22, `fat-pack` ~$10.14.
