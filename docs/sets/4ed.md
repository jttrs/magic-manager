# `4ed` — Fourth Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `4ed` or working on `4ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `4ed`
**Family root type:** `core`
**Family released:** 1995-04-01
**Last audit:** 2026-11-06 via `/characterize-set 4ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, white border, nonfoil only.** 15 basics. Its child `4bb` (Fourth Edition Foreign Black Border) is ~1871 non-English prints, absent locally.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `4ed` | core | 378 | 1995-04-01 | parent — 1–363 + basics 364–378 |
| `4bb` | core | 378 cards / ~1871 prints (0 local) | 1995-04-01 | Foreign Black Border — French, German, Italian, Spanish, Portuguese, Japanese, Korean, Traditional Chinese; unpriced; not synced |

`set:4ed+related` covers both.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 378 | `4ed` 1–378 (121 C / 121 U / 121 R + 15 basics) | `regular` | rarity/base sub-selectors — R ≈ $423 (Mana Vault 334 ~$96, Sylvan Library 273 ~$33, Land Tax 34 ~$20, Strip Mine 363 ~$19, Birds of Paradise 234 ~$18, Winter Orb 358 ~$16) |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] 4ed = []` (2026-11-08) to enable `mm query missing-set 4ed`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 4ed = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `4bb` Foreign Black Border | ~1871 (0 local) | **owner's call** — non-English only, not syncable |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **2 German `N†` variation prints** (Drudge Skeletons 107†, El-Hajjâj 134†) exist on Scryfall; not local. Scryfall's search leaves out `variation` prints, so `mm set sync` never fetches them.
- **`4bb` is non-English** (eight languages, one print per language per card).
- **No foils.**
- MTGJSON: Fourth Edition Gift Box (`multiple_decks` / `two_player_starter`), Starter Deck (a `starter` booster type).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] 4ed = []` — configured 2026-11-08 (enables `mm query missing-set 4ed`).
- `config/families.toml` `[[unobtainable.4ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.4ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |
| Starter Deck | starter deck | — |
| Gift Box | starter set | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 4ed --list-boosters` (2026-11-06): `default` EV ~$9.01, `starter` ~$35.40.
