# `gk2` — RNA Guild Kit

> Per-family memory doc. Read this before answering set-specific questions about
> `gk2` or working on `gk2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gk2`
**Family root type:** `box` (standalone, `parent_set_code: null`)
**Family released:** 2019-02-15
**Last audit:** 2026-11-05 via `/characterize-set gk2` (one-at-a-time run — tier decisions pending owner review).

---

> **Five fixed reprint decks, one per Ravnica Allegiance guild** (Azorius,
> Orzhov, Rakdos, Gruul, Simic). Every card is a reprint of an older Ravnica
> card; each kit's leader is a foil-only legend. Base frame, no treatments.
> Sibling: `gk1` (GRN Guild Kit), its own family. Not reached by
> `set:rna+related`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gk2` | box | 133 | 2019-02-15 | parent — five kits in CN order: Azorius 1–27, Orzhov 28–51, Rakdos 52–79, Gruul 80–106, Simic 107–133 |
| `tgk2` | token | 9 | 2019-02-15 | tokens |

`set:gk2+related` covers both. `box` isn't a default inventory set type, but the
anchor is always included by `mm set master-list gk2`.

---

## 2. Treatments

Every print computes `regular`; no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| kit leaders (**foil-only**) | 5 | `gk2` 1 Isperia, 28 Teysa, 52 Rakdos ~$5, 80 Ruric Thar, 107 Zegana | `regular` | rare/mythic-regular |
| kit cards (nonfoil-only) | 128 | `gk2` 2–133 minus the leaders (9 M / 46 R / 49 U / 29 C in all) | `regular` | rarity sub-selectors — Utvara Hellkite 59 ~$15, Birds of Paradise 82 ~$11, Protean Hulk 83 ~$7. Set ≈ $95 nonfoil |
| tokens | 9 | `tgk2` 1–9 | `regular` | tokens |

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] gk2 = []` to enable `mm query missing-set gk2`.

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
| `[dupe_foil] gk2 = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 133 | **owner's call** — all reprints, mostly with their original art (106 of 133 share an earlier illustration locally); a completion target only for a Guild Kit collector |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **All reprints.** 13 prints show no earlier printing locally only because
  their original sets aren't synced (see [`c19`](c19.md) §7).
- **Finish splits by role:** the five leaders are foil-only, everything else
  nonfoil-only.
- **Each kit is a CN block**, so a kit's cards can be selected with
  `cn>=`/`cn<=` (e.g. Gruul = `set:gk2 cn>=80 cn<=106`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gk2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gk2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Guild Kit ×5 | Guild kit (MTGJSON `kit` / `guild_kit`; in `PRECON_MODERN_TYPES`) | Azorius, Gruul, Orzhov, Rakdos, Simic — fileNames `<Guild>_GK2`; also a Set of 5 |

**Booster types (for `sealed-value` EV):** none.
