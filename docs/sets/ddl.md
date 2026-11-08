# `ddl` — Duel Decks: Heroes vs. Monsters

> Per-family memory doc. Read this before answering set-specific questions about
> `ddl` or working on `ddl`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddl`
**Family root type:** `duel_deck`
**Family released:** 2013-09-06
**Last audit:** 2026-11-05 via `/characterize-set ddl` (one-at-a-time run — tier decisions pending owner review).

---

> **Two Theros-themed reprint decks** led by foil-only mythics (Sun Titan,
> Polukranos). Standalone root. Same shape as [`ddm`](ddm.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddl` | duel_deck | 81 | 2013-09-06 | parent — Heroes deck 1–42 (R/W), Monsters deck 43–81 (R/G) |
| `tddl` | token | 2 | 2013-09-06 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddl`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddl` 1 Sun Titan (~$2.19), 43 Polukranos, World Eater (~$0.79; new art) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 79 | the rest (Pyrokinesis 32 ~$2.20, Skarrg 73, Orcish Lumberjack 44) | `regular` | rarity sub-selectors — ≈ $22 |

**New art (local check, 9):** Sun Titan 1, Daily Regimen 18, Stand Firm 21,
Griffin Guide 28, Polukranos 43, Ghor-Clan Savage 53, Deus of Calamity 54,
Skarrgan Skybreaker 60, Shower of Sparks 61. Configured `[dupe_foil] ddl = []` (2026-11-08).

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddl = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- MTGJSON decks `Heroes` / `Monsters` (`type: Duel Deck`).
- Polukranos 43 here predates its `ths` printing by three weeks.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddl = []` — configured 2026-11-08 (enables `mm query missing-set ddl`).
- `config/families.toml` `[[unobtainable.ddl.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddl]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Heroes vs. Monsters | Duel deck | Heroes 1–42, Monsters 43–81 |

**Booster types (for `sealed-value` EV):** none.
