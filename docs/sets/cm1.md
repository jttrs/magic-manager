# `cm1` — Commander's Arsenal

> Per-family memory doc. Read this before answering set-specific questions about
> `cm1` or working on `cm1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cm1`
**Family root type:** `arsenal`
**Family released:** 2012-11-02
**Last audit:** 2026-11-05 via `/characterize-set cm1` (one-at-a-time run — tier decisions pending owner review).

---

> **Premium Commander box: 18 foil-only reprints plus 10 oversized foil
> commanders.** Standalone root. The 18 cards include a ~$133 foil Rhystic
> Study (rated common).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cm1` | arsenal | 18 | 2012-11-02 | parent — CN 1–18, alphabetical |
| `ocm1` | memorabilia | 10 | 2012-11-02 | oversized foil commanders 1–10 (Sliver Queen 9 ~$147, Azusa 1 ~$15, Karrthus 7, Karn 6) |

`arsenal` isn't a default inventory set type, but the anchor is always
included by `mm set master-list cm1`; `ocm1` (memorabilia) is off by default.

---

## 2. Treatments

All `regular`, foil-only. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| reprints (foil) | 18 | `cm1` 1–18 (2 C / 1 U / 11 R / 4 M; Rhystic Study 15 ~$133, Scroll Rack 16 ~$42, Sylvan Library 17 ~$38, Command Tower 2 ~$30, Diaochan 5 ~$20) | `regular` | rarity sub-selectors — ≈ $336 foil |
| oversized commanders | 10 | `ocm1` 1–10 (foil) | `regular` | memorabilia, off by default — ≈ $214 |

Proposed `[dupe_foil] cm1 = []` to enable `mm query missing-set cm1`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] cm1 = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Rhystic Study 15 and Command Tower 2 are commons** here, so
  missing-set's rare/mythic sub-selectors skip the most valuable card.
- **`ocm1` Sliver Queen 9 (~$147)** is the priciest oversized card in the
  run, but memorabilia is off by default.
- MTGJSON decklist `Commander's Arsenal` (`type: Box Set`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.cm1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cm1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander's Arsenal | box set (`arsenal`) | 18 foils + 10 oversized commanders |

**Booster types (for `sealed-value` EV):** none.
