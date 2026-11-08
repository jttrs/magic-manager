# `shm` — Shadowmoor

> Per-family memory doc. Read this before answering set-specific questions about
> `shm` or working on `shm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `shm`
**Family root type:** `expansion`
**Family released:** 2008-05-02
**Last audit:** 2026-11-05 via `/characterize-set shm` (one-at-a-time run — tier decisions pending owner review).

---

> **Hybrid-mana set (Painter's Servant, Greater Auramancy, Reflecting Pool).** **No mythics.** Quirk: **Reflecting Pool is split by finish** — nonfoil `278`, foil `278★`, same art.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `shm` | expansion | 302 | 2008-05-02 | parent — booster set 1–301 (basics 282–301) + Reflecting Pool `278★` (foil) |
| `pshm` | promo | 2 | 2008-05-02 | prerelease Demigod of Revenge `183★` (alt art, `datestamped`) + release Vexing Shusher `222★` (same art, ~$12) |
| `tshm` | token | 12 | 2008-05-02 | tokens |

`set:shm+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 301 | `shm` 1–301 (141 C / 80 U / 80 R (incl. 278★)) | `regular` | rarity/base sub-selectors — R+M ≈ $421 nonfoil / $2445 foil (Reflecting Pool `278★` ~$96 foil / 278 ~$21, Painter's Servant 257 ~$50 / $126, Greater Auramancy 7 ~$40, Wound Reflection 81, Plague of Vermin 73) |
| Reflecting Pool foil | 1 | `shm` `278★` (foil-only, **same art** as 278 which is nonfoil-only; not in MTGJSON's booster sheets) | `regular` | **one card, two rows** — the foil is `278★` |

**`promo_types`:** the prerelease Demigod `183★` has its own art; the release Vexing Shusher `222★` reuses the booster art. The prerelease is `datestamped` (dropped by `missing.drop_datestamped_with_sibling`); the release foil isn't, so missing-set lists it. No fancy-foil sheet →
proposed `[dupe_foil] shm = []` to enable `mm query missing-set shm`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] shm = []` | 0 | **apply** — empty, enables missing-set |
| `pshm` promos | 2 | **owner's call** — 1 of 2 has its own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `183★` | `pshm` | prerelease (alt art) | Demigod of Revenge |
| `222★` | `pshm` | release (same art) | Vexing Shusher |

---

## 7. Edge cases & gotchas

- **Foil Reflecting Pool is `278★`**, not a foil of 278 (same pattern as the [`frf`](frf.md) Sieges).
- **Extreme foil premium** (rares ~$421 nonfoil vs ~$2,445 foil incl. the ★).
- MTGJSON lists a `tournament` booster type (~$64.85).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.shm.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.shm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / tournament packs | booster product | — |
| Theme Decks ×5 | theme deck | — |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py shm --list-boosters` (2026-11-05): `draft` EV ~$15.89; `tournament` ~$64.85.
