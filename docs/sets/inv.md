# `inv` — Invasion

> Per-family memory doc. Read this before answering set-specific questions about
> `inv` or working on `inv`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `inv`
**Family root type:** `expansion`
**Family released:** 2000-10-02
**Last audit:** 2026-11-06 via `/characterize-set inv` (one-at-a-time run — tier decisions pending owner review).

---

> **First Invasion-block set (multicolour), old border, no mythics.** 20 basics. Two commons have an extra **foil-only `N★` print tagged `schinesealtart`** (the art used for Chinese printings). Its only promo is a **Latin** prerelease foil, which can't be synced.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `inv` | expansion | 352 (354 on Scryfall) | 2000-10-02 | parent — booster set 1–350 (basics 331–350) + 124★ / 134★ |
| `pinv` | promo | 1 (0 local) | 2000-10-02 | prerelease Raging Kavu `262` — **Latin** (`lang = la`), foil, `datestamped`, ~$15; not synced |

`set:inv+related` covers all. The 2 Scryfall-only rows are the Simplified-Chinese prints Soul Burn 124s and Urborg Skeleton 134s (`lang = zhs`), never synced.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 350 | `inv` 1–350 (130 C / 110 U / 110 R; basics 331–350) | `regular` | rarity/base sub-selectors — R ≈ $405 nonfoil / $4899 foil (Phyrexian Altar 306 ~$61 / ~$530 foil, Elvish Champion 186 ~$27, Tsabo's Web 317 ~$24, Aura Shards 233 ~$23, Spirit of Resistance 38 ~$20) |
| `schinesealtart` foils | 2 | `inv` 124★ Soul Burn (same art as 124), 134★ Urborg Skeleton (**own art**) — foil-only, common, unpriced | `regular` | common sub-selectors don't list commons in missing-set; harmless |

**`promo_types`:** `schinesealtart` on 124★ / 134★ marks the Chinese-printing art; no dupe signal. `pinv` holds one Latin prerelease Raging Kavu `262`; `mm set sync pinv` 404s (English-only). No fancy-foil sheet →
configured `[dupe_foil] inv = []` (2026-11-08) to enable `mm query missing-set inv`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] inv = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pinv` promo | 1 (0 local) | **owner's call** — Latin-only, not syncable |
| `schinesealtart` `N★` | 2 | **owner's call** — unpriced English foils of the Chinese art; 134★ has unique art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `262` | `pinv` | prerelease (Latin) | Raging Kavu |
| `N★` | `inv` | Chinese-art foil (`schinesealtart`) | Urborg Skeleton 134★ |

---

## 7. Edge cases & gotchas

- **Same Chinese-art pattern as [`7ed`](7ed.md)** (skeletons and skulls were redrawn for Chinese printings), but here the `N★` rows are English and local, while the `Ns` rows are `zhs` and not.
- **`pinv` is non-English** (Latin). The novelty-language prerelease run continues in [`pls`](pls.md) (Ancient Greek), [`apc`](apc.md) (Sanskrit), [`ody`](ody.md) (Arabic).
- **No mythics**; foil rares ~12× nonfoil.
- MTGJSON: 4 Theme Decks (Blowout, Dismissal, Heavy Duty, Spectrum), Tournament Pack, Fat Pack, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] inv = []` — configured 2026-11-08 (enables `mm query missing-set inv`).
- `config/families.toml` `[[unobtainable.inv.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.inv]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Tournament Pack | starter-size sealed pack | — |
| Theme Decks ×4 | theme deck | not in `PRECON_MODERN_TYPES` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py inv --list-boosters` (2026-11-06): `draft` EV ~$9.18, `fat-pack` ~$10.36, `tournament` ~$51.13.
