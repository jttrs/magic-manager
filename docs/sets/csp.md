# `csp` — Coldsnap

> Per-family memory doc. Read this before answering set-specific questions about
> `csp` or working on `csp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `csp`
**Family root type:** `expansion`
**Family released:** 2006-07-21
**Last audit:** 2026-11-06 via `/characterize-set csp` (one-at-a-time run — tier decisions pending owner review).

---

> **Stand-alone Ice Age-themed set, pre-mythic.** Old border-era rarity: **no mythics** (C/U/R). A `box` child, `cst`, holds the Theme Deck reprints of Ice Age cards.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `csp` | expansion | 155 | 2006-07-21 | parent — booster set 1–155 (basics 151–155, snow-covered) |
| `pcsp` | promo | 2 | 2006-07-21 | prerelease Allosaurus Rider `101★` (alt art, `datestamped`) + release Marit Lage token `1` (`is_token = 1`) |
| `cst` | box | 62 | 2006-07-21 | **Coldsnap Theme Deck reprints** — Ice Age-era cards on their original CNs (some `a`/`b` art variants: 9b, 12b, 30b, 44b, 51a, 57a, 72a, 86a); nonfoil-only |

`set:csp+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 155 | `csp` 1–155; 5 snow-covered basics 151–155 (60 C / 55 U / 40 R) | `regular` | rarity/base sub-selectors — R+M ≈ $184 nonfoil / $1557 foil (Thrumming Stone 142 ~$23, Braid of Fire 78 ~$22, Soul Spike 70 ~$18, Arcum Dagsson 27 ~$17 / ~$111 foil, Commandeer 29 ~$393 foil) |
| Theme Deck reprints (`cst`) | 62 | `cst` (42 C / 20 U, nonfoil) | `regular` | rarity sub-selectors — ≈ $47; Dark Ritual 120 ~$5, Brainstorm 61 ~$1.59 |

**`promo_types`:** the prerelease Allosaurus Rider `101★` (~$12.56) has its own art; the release promo is a Marit Lage token, dropped as a token. The prerelease carries `datestamped`, so `missing.drop_datestamped_with_sibling` drops it from missing-set. No fancy-foil sheet →
proposed `[dupe_foil] csp = []` to enable `mm query missing-set csp`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] csp = []` | 0 | **apply** — empty, enables missing-set |
| `pcsp` promos | 2 | **owner's call** — the prerelease has its own art; the other is a token |
| `cst` Theme Deck reprints | 62 | **owner's call** — `box` reprints shipped only in Coldsnap Theme Decks; kept (default) — pending owner review |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `101★` | `pcsp` | prerelease (alt art) | Allosaurus Rider |
| `1` | `pcsp` | release (token) | Marit Lage |

---

## 7. Edge cases & gotchas

- **`cst` uses Ice Age CNs** with `a`/`b` suffixes for the alternate arts; pair CN with set code.
- **No mythics**; foil commons/rares carry a big premium (Commandeer ~$393 foil).
- MTGJSON: 4 Theme Decks, a Bundle Land Pack, MTGO Redemption (none in `PRECON_MODERN_TYPES`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.csp.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.csp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×4 | theme deck | each with a `cst` reprint pack |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py csp --list-boosters` (2026-11-06): `draft` EV ~$14.88.
