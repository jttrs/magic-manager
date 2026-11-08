# `gk1` — GRN Guild Kit

> Per-family memory doc. Read this before answering set-specific questions about
> `gk1` or working on `gk1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gk1`
**Family root type:** `box` (standalone, `parent_set_code: null`)
**Family released:** 2018-11-02
**Last audit:** 2026-11-05 via `/characterize-set gk1` (one-at-a-time run — tier decisions pending owner review).

---

> **Five fixed reprint decks, one per Guilds of Ravnica guild** (Dimir, Izzet,
> Golgari, Boros, Selesnya). Every card is a reprint of an older Ravnica card;
> each kit's leader is a foil-only legend. Base frame, no treatments. Sibling:
> [`gk2`](gk2.md) (RNA Guild Kit), its own family. Not reached by
> `set:grn+related`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gk1` | box | 127 | 2018-11-02 | parent — five kits in CN order: Dimir 1–25, Izzet 26–49, Golgari 50–76, Boros 77–101, Selesnya 102–127 (each block ends with its two basics) |
| `tgk1` | token | 10 | 2018-11-02 | tokens |

`set:gk1+related` covers both. `box` isn't a default inventory set type, but the
anchor is always included by `mm set master-list gk1`.

---

## 2. Treatments

Every print computes `regular`; no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| kit leaders (**foil-only**) | 5 | `gk1` 1 Etrata, 26 Niv-Mizzet, the Firemind, 50 Izoni, 77 Aurelia, the Warleader ~$17, 102 Trostani | `regular` | rare/mythic-regular |
| kit cards (nonfoil-only) | 122 | `gk1` 2–127 minus the leaders (6 M / 44 R / 41 U / 36 C in all) | `regular` | rarity sub-selectors — Deathrite Shaman 59 ~$8, Legion Loyalist 82 ~$7, Savra 69 ~$5, Boros Charm 84 ~$5. Set ≈ $89 nonfoil |
| tokens | 10 | `tgk1` | `regular` | tokens |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] gk1 = []` to enable `mm query missing-set gk1`.

**Full-art convention:** none.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

None configured, none needed.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gk1 = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 127 | **owner's call** — all reprints, mostly with their original art (108 of 127 share an earlier illustration locally); same decision as [`gk2`](gk2.md) |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **All reprints**; finish splits by role (leaders foil-only, the rest
  nonfoil-only).
- **Each kit is a CN block**, so a kit's cards select with `cn>=`/`cn<=`
  (e.g. Golgari = `set:gk1 cn>=50 cn<=76`).
- Aurelia, the Warleader 77 (foil) is the family's most valuable print.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gk1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gk1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Guild Kit ×5 | Guild kit (MTGJSON `type: Guild Kit`; in `PRECON_MODERN_TYPES`) | Boros, Dimir, Golgari, Izzet, Selesnya — fileNames `<Guild>_GK1` |

**Booster types (for `sealed-value` EV):** none.
