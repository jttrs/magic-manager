# `ddp` — Duel Decks: Zendikar vs. Eldrazi

> Per-family memory doc. Read this before answering set-specific questions about
> `ddp` or working on `ddp`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddp`
**Family root type:** `duel_deck`
**Family released:** 2015-08-28
**Last audit:** 2026-11-05 via `/characterize-set ddp` (one-at-a-time run — tier decisions pending owner review).

---

> **Two reprint decks** led by foil-only mythics (Avenger of Zendikar, Oblivion
> Sower). Standalone root, **no token set**: tokens are `ddp` 76–80. Same shape
> as [`ddq`](ddq.md) / [`ddr`](ddr.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddp` | duel_deck | 80 | 2015-08-28 | parent — Zendikar deck 1–40, Eldrazi deck 41–75 (Swamps 70–72, Mountains 73–75), tokens 76–80 |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list ddp`.

---

## 2. Treatments

All `regular` except two full-art tokens (`fa`). `frame_effects` `devoid` (2)
is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddp` 1 Avenger of Zendikar (~$3.94), 41 Oblivion Sower (~$1.22) | `regular` | mythic-regular — both new art |
| deck cards (nonfoil-only) | 73 | `ddp` 2–40, 42–75 (It That Betrays 43 ~$11, Pawn of Ulamog 55, Eldrazi Temple 68) | `regular` | rarity sub-selectors — ≈ $34 |
| tokens | 5 | `ddp` 76–78 Eldrazi Spawn, 79 Hellion, 80 Plant (`is_token = 1`) | `regular` / `fa` | tokens — dropped by missing-set |

**New art (local check):** Avenger 1, Primal Command 20, Oblivion Sower 41,
Consume the Meek 49 (+ two tokens).

Configured `[dupe_foil] ddp = []` (2026-11-08) to enable `mm query missing-set ddp`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] ddp = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Tokens live in the parent set** at 76–80.
- **Only the two face mythics are foil** (foil-only).
- MTGJSON decks `Zendikar` / `Eldrazi` (`type: Duel Deck`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddp = []` — configured 2026-11-08 (enables `mm query missing-set ddp`).
- `config/families.toml` `[[unobtainable.ddp.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddp]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Zendikar vs. Eldrazi | Duel deck | Zendikar 1–40, Eldrazi 41–75 |

**Booster types (for `sealed-value` EV):** none.
