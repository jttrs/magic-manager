# `drb` — From the Vault: Dragons

> Per-family memory doc. Read this before answering set-specific questions about
> `drb` or working on `drb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `drb`
**Family root type:** `from_the_vault`
**Family released:** 2008-08-29
**Last audit:** 2026-11-05 via `/characterize-set drb` (one-at-a-time run — tier decisions pending owner review).

---

> **The first From the Vault: 15 foil-only dragon reprints. Standalone root, no children. Unlike later boxes the cards are rated **rare**, not mythic.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `drb` | from_the_vault | 15 | 2008-08-29 | parent — CN 1–15, alphabetical (Bladewing the Risen 1 … Two-Headed Dragon 15) |

The anchor is always included by `mm set master-list drb`, whatever its
`set_type`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| reprints | 15 | `drb` 1–15 (Kokusho 9 ~$34, Dragonstorm 5 ~$20, Bladewing 1 ~$16, Draco 3 ~$12, Nicol Bolas 10 ~$11, Niv-Mizzet 11) | `regular` | **rare**-regular — ≈ $145 foil |

**New art (local check):** 14 of 15 first seen here (Ebon Dragon 6 reuses its older art). Proposed `[dupe_foil] drb = []` to enable
`mm query missing-set drb`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: none
configured yet (proposals pending owner review); `[dupe_foil] drb = []` —
**apply**.

---

## 7. Edge cases & gotchas

- **Rarity is `rare`**, not mythic (mythic rarity arrived with Shards of Alara a month later), so a `rarity=mythic` filter misses this box.
- **Code `drb`**, not `v08`.
- MTGJSON decklist `From the Vault: Dragons` (`type: Box Set`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.drb.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.drb]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| From the Vault: Dragons | box set (`from_the_vault`) | 15 cards |

**Booster types (for `sealed-value` EV):** none.
