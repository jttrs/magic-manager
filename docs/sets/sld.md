# `sld` — Secret Lair Drop

> Per-family memory doc. Read this before answering set-specific questions about
> `sld` or working on `sld`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `sld`
**Family root type:** `box` (an ongoing direct-to-consumer product line, not a set)
**Family released:** 2019-12-02 (ongoing — newest local print 2026-11-13)
**Last audit:** 2026-11-04 via `/characterize-set sld` (one-at-a-time run — aggregate audit; tier decisions pending owner review).

---

> **Not a set: a catalog of ~780 separate drops** (MTGJSON lists 781
> `type: Secret Lair Drop` decklists, 2019-12-03 → 2026-12-14). Each drop is
> a small fixed bundle of cards, usually sold in a regular and a foil edition.
> Track it **by drop**, not as a "complete the set" family. The drop-grain
> tools are the `bulk-add` skill (add a drop by CN range), `sld.py`
> (`collect_drop_ids`, `recent_drops`), `sld_market.py` / the
> `secret-lair-value` skill (sealed vs cards), and product true-up (a complete
> drop folds in as one product). This doc records the family's shape so those
> tools are read correctly.

## 1. Family map

| Code | `set_type` | Cards (local) | Released | Notes |
|---|---|---:|---|---|
| `sld` | box | 2,843 (Scryfall says 2,871; a few newest prints not synced) | 2019-12-03 → 2026-11-13 | parent — every regular drop |
| `slp` | promo | 57 | 2023-02-19 → 2027-01-08 | Secret Lair Promo — store/event promos (Brainstorm 1, Ragavan 2, Ugin 6; Tamiyo 49 foil ~$5,600, Kozilek's Command 52 foil ~$3,200) |
| `slc` | box | 114 | 2022-11-01 → 2026-11-02 | Secret Lair Countdown (began with the 2022 30th-anniversary Countdown Kit; added to through 2026) |
| `slx` | masters | 30 | 2022-03-03 → 2025-04-25 | Universes Within (in-universe renames of Universes Beyond cards) |
| `slu` | box | 16 | 2020-06-12 → 2021-03-05 | Secret Lair: Ultimate Edition |
| `pssc` | memorabilia | 10 | 2025-02-21 | Secret Lair Showcase Planes (oversized, unpriced) |

`set:sld+related` covers all six (3,070 prints). Master-list / Collection skip
`pssc` (memorabilia) by default.

---

## 2. Treatments

Survey (`survey_treatment_signature.py SLD`, 3,070 prints). Treatments are
spread across hundreds of drops rather than set by CN band, so this table is
by computed class, not band.

| Class | Prints | Computed treatment | Notes |
|---|---:|---|---|
| borderless | ~2,570 (1,331 foil / 1,241 nonfoil rows) | `b` | the house style — most drops are borderless |
| plain frame | ~1,075 rows | `regular` | black-border drops in a normal frame |
| full-art | ~750 rows | `fa` | full-art drops (incl. many basic-land drops) |
| fancy-foil borderless / full-art | 176 + 68 + 20 + 5 etched | `b\|ff`, `fa\|ff`, `ff` | rainbowfoil (191), halofoil (41), galaxyfoil (20), confettifoil (18), raisedfoil (15), dazzlefoil (7), neonink (4), gilded (3), stepandcompleat (9) |
| showcase (incl. borderless / fancy-foil) | ~138 rows | `shw`, `b\|shw`, `shw\|ff`, `b\|shw\|ff` | showcase-frame drops |
| extended-art | 101 rows | `ext` | ext-frame drops (auto-dropped by the preferred filter) |
| etched-only | 48 rows | `regular` / `b` / `fa` `[etched]` | — |

Counts are print-rows by finish, from the survey.

**`promo_types` signals that matter:**

| promo_type | Prints | What it marks |
|---|---:|---|
| `universesbeyond` | 926 | licensed crossover drops (FF, Walking Dead, Fortnite, …) |
| `sldbonus` | 522 | the drop's **bonus card** (one random extra per order); includes the named-code CNs `SCTLR` and `VS` |
| `poster` | 302 | Scryfall `poster` tag (e.g. CN 138–140 Anguished Unmaking / Assassin's Trophy / Decimate) |
| `serialized` | 6 | numbered cards: `sld` 713–717 (Swords to Plowshares ~$1,702, Lord of the Pit, Merfolk of the Pearl Trident, Shivan Dragon, Giant Growth) + `VS` Viscera Seer |
| `thick` | 17 | thick-stock prints |
| `ffiv`…`ffxvi` | 25 | Final Fantasy drop tags |

**Full-art convention:** full-art is a per-drop choice, not a family rule.

---

## 3. Chase variants

- **Serialized** `sld` 713–717 and `VS`.
- **Bonus cards** (`sldbonus`) are the per-drop chase. They're a random extra,
  so they're not guaranteed in a sealed drop.
- Top prices (local): `slp` 49 Tamiyo foil ~$5,600, `sld` 796★ Mana Vault foil
  ~$4,500, `slp` 52 Kozilek's Command foil ~$3,200, `sld` 808 Snapcaster Mage
  ~$1,750, `sld` 713 Swords to Plowshares ~$1,702, `sld` 7004 Solitude / 7005
  Subtlety foil ~$900–$1,000.

---

## 4. Scenes / posters / panoramas

Many drops are art series (four or five cards by one artist or theme), but none
are configured as scenes. Per-drop grouping comes from MTGJSON decklists via
`sld.py`, not `[[scenes.sld]]`.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] sld` | — | **do NOT add** — leave missing-set disabled for SLD. `set:sld+related` has 2,892 rare/mythic prints worth ≈ $35.4k nonfoil / $68.4k foil (sld + slp + slc + slx + slu); a "missing from Secret Lair" list isn't a useful shopping list. Use the drop-grain tools instead |
| `slp` / `slc` / `slu` / `slx` | 217 | n/a while missing-set is disabled. If ever enabled, `slp` (store/event promos) is the obvious exclusion |
| `pssc` | 10 | memorabilia — already off |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `1`–`~2,700` | `sld` | regular drops, numbered in release order (0–999, 1000s from 2022, 2000s from 2025) | — |
| `7001`+ (149 prints) | `sld` | 2025+ drops numbered in the 7000s | Solitude 7004, Subtlety 7005 |
| `9990`–`9999` | `sld` | ten 2022–2024 one-offs | Sisay 9999 |
| `N★`, `Na`/`Nb` | `sld` | foil-only or variant prints of a drop card (140 non-numeric CNs total) | Mana Vault 796★ |
| `SCTLR`, `VS`, `IFIYW-1`…`10` | `sld` | named-code specials (bonus cards, an April-2026 drop) | Viscera Seer `VS` |
| `slp` `N` | `slp` | store / event promos | Ragavan 2 |

---

## 7. Edge cases & gotchas

- **CN order ≠ drop order across bands.** The 0–999, 1000s, 2000s and 7000s
  bands overlap in release date. Sort by `released_at`, never by CN, to get
  "newest drops".
- **Local count lags Scryfall.** `sld` is synced at a point in time; a drop
  announced after the last `mm set sync sld` is missing locally. Re-sync before
  any drop-level question about recent releases.
- **Foil vs regular editions** are usually the same CN in two finishes, but
  some drops give the foil its own `★` CN.
- **Bonus cards may not be in the drop's MTGJSON decklist**. Sealed valuation
  bridges them from `contents.card` uuids (see CLAUDE.md `market._sld_cost`).
- `promo_types` include `stepandcompleat` (9) and the fancy foils above.
  `stepandcompleat` is not in `FANCY_FOIL_PROMO_TYPES` (see [`khm`](khm.md) §7).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.sld.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.sld]]` — none.
- Drop-grain code (not family config): `src/magic_manager/sld.py`, `sld_market.py`, `valuation.sld_sealed_product`, `trueup` (complete drops as products).

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Secret Lair Drop (regular / foil editions) | Secret Lair | ~780 drops; MTGJSON `type: Secret Lair Drop` (excluded from `precon-list` via `PRECON_EXCLUDED_TYPES`) |
| Secret Lair Countdown Kit | Secret Lair | `slc` |
| Secret Lair: Ultimate Edition | Secret Lair | `slu` |
| Store / event promos | promo | `slp` |

**Booster types (for `sealed-value` EV):** none at the family level. Value
drops with the `secret-lair-value` skill or `sealed-value` per drop.
