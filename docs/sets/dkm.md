# `dkm` — Deckmasters

> Per-family memory doc. Read this before answering set-specific questions about
> `dkm` or working on `dkm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dkm`
**Family root type:** `box`
**Family released:** 2001-12-01
**Last audit:** 2026-11-06 via `/characterize-set dkm` (one-at-a-time run — tier decisions pending owner review).

---

> **Garfield vs. Finkel two-player tin** (2001): two 40-card Ice Age-block
> reprint decks. Standalone root, no children, no tokens. Mostly nonfoil; four
> foil-only prints. Several commons come in two arts as `Na`/`Nb`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dkm` | box | 58 | 2001-12-01 | parent — Garfield (black/red) 1–21, Finkel (green/artifact) 22–41, basics 42–50 |

No children. `box` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dkm`.

---

## 2. Treatments

Every print computes `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck cards (nonfoil-only) | 45 | `dkm` 1–41 minus 7/29, with 6 `a`/`b` pairs | `regular` | rarity sub-selectors — rares ≈ $28 (Sulfurous Springs 40 ~$9, Underground River 41 ~$7, Jokulhaups 15 ~$6, Karplusan Forest 39 ~$5) |
| foil-only rares | 2 | `dkm` 7 Necropotence (~$179), 29 Lhurgoyf (~$3) | `regular` | rare-regular — **Necropotence is 85% of the set's value** |
| foil `★` doubles | 2 | `dkm` 14★ Incinerate (~$9), 36★ Icy Manipulator (~$1.33) | `regular` | **same art** as nonfoil 14 / 36 (finish split, like [`9ed`](9ed.md)) |
| `a`/`b` art pairs | 12 | `dkm` 6, 8, 13, 21, 31, 37 | `regular` | **different art** per letter — distinct printings |
| basics | 9 | `dkm` 42–50 (Swamp, Mountain, Forest ×3) | `regular` | basics |

**New art (local check):** 30 prints have art seen nowhere else locally.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] dkm = []` to enable `mm query missing-set dkm`.

---

## 3. Chase variants

Foil Necropotence 7 (~$179).

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dkm = []` | 0 | **apply** — empty, enables missing-set |
| foil `★` doubles 14★ / 36★ | 2 | **owner's call** — same-art foil of a nonfoil print (part of the finish-split decision) |
| whole family | 58 | **owner's call** — a one-time box product; kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Foil-only vs nonfoil-only:** each print is one finish. The `★` CN is the
  foil half of a card that also has a nonfoil CN; Necropotence and Lhurgoyf
  exist **only** as foils.
- **`a`/`b` CNs are separate arts**, not finishes (Lim-Dûl's High Guard 6a/6b,
  Phantasmal Fiend 8a/8b, Guerrilla Tactics 13a/13b, Storm Shaman 21a/21b,
  Yavimaya Ancients 31a/31b, Phyrexian War Beast 37a/37b).
- Some commons are unpriced (Phantasmal Fiend 8a, Storm Shaman 21a, Folk of the
  Pines 25).
- MTGJSON: sealed product *Garfield vs Finkel 2001 Deckmasters Tin*
  (`box_set` / `other`) and decks `Garfield` / `Finkel` typed `Theme Deck`
  (not in `PRECON_MODERN_TYPES`, so not in `mm set precon-list`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dkm.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dkm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Deckmasters tin | box set (MTGJSON `box_set` / `other`) | two 40-card decks (Garfield, Finkel) |

**Booster types (for `sealed-value` EV):** none.
