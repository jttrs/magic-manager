# `chr` — Chronicles

> Per-family memory doc. Read this before answering set-specific questions about
> `chr` or working on `chr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `chr`
**Family root type:** `masters`
**Family released:** 1995-07-01
**Last audit:** 2026-11-06 via `/characterize-set chr` (one-at-a-time run — tier decisions pending owner review).

---

> **English reprint set** of Arabian Nights / Antiquities / Legends / The Dark cards, white border, nonfoil only. The three Urza lands come in **four arts each** (`114a`–`116d`). Its child `bchr` is a Japanese black-border printing, absent locally.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `chr` | masters | 125 | 1995-07-01 | parent — CN 1–116; Urza's Mine / Power Plant / Tower at `114a`–`d`, `115a`–`d`, `116a`–`d` |
| `bchr` | masters | 125 (0 local) | 1995-07-01 | Chronicles Foreign Black Border — **Japanese** only (`lang = ja`), unpriced; not synced |

`set:chr+related` covers both. `masters` isn't a default inventory set type, but the anchor is always included by `mm set master-list chr`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 113 | `chr` 1–113 (37 C / 31 U / 45 R) | `regular` | rarity/base sub-selectors — R ≈ $109 (Concordant Crossroads 60 ~$36, City of Brass 112 ~$29, Ashnod's Altar 92 ~$14, Blood Moon 46 ~$9, Nicol Bolas 81 ~$6) |
| Urza lands ×4 arts | 12 | `chr` 114a–116d (uncommon) | `regular` | **different art** per letter — distinct printings; ≈ $11 total |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] chr = []` to enable `mm query missing-set chr`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] chr = []` | 0 | **apply** — empty, enables missing-set |
| `bchr` Japanese black border | 125 (0 local) | **owner's call** — Japanese-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `114a`–`116d` | `chr` | Urza land art variants | Urza's Tower 116c |

---

## 7. Edge cases & gotchas

- **`a`–`d` CNs are separate arts** for the three Urza lands.
- **`bchr` is non-English** (Japanese): nothing local. Its French / German / Italian counterparts are [`ren`](ren.md) and [`rin`](rin.md).
- **No foils.** MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.chr.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.chr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py chr --list-boosters` (2026-11-06): `default` EV ~$7.91.
