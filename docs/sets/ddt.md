# `ddt` — Duel Decks: Merfolk vs. Goblins

> Per-family memory doc. Read this before answering set-specific questions about
> `ddt` or working on `ddt`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddt`
**Family root type:** `duel_deck`
**Family released:** 2017-10-24
**Last audit:** 2026-11-05 via `/characterize-set ddt` (one-at-a-time run — tier decisions pending owner review).

---

> **Two 60-card tribal reprint decks**, each led by a foil-only mythic.
> Standalone root. Base frame only. Same shape as [`ddu`](ddu.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddt` | duel_deck | 63 | 2017-10-24 | parent — Merfolk deck 1–31 (basics 28–31), Goblins deck 32–63 (basics 60–63) |
| `tddt` | token | 3 | 2017-10-24 | tokens (Elemental, Wall, Goblin) |

`set:ddt+related` covers both. `duel_deck` isn't a default inventory set type,
but the anchor is always included by `mm set master-list ddt`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddt` 1 Master of Waves (~$0.45), 32 Warren Instigator (~$18) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 61 | `ddt` 2–31, 33–63 (Misdirection 15 ~$13, Goblin Chieftain 41 ~$5, Relentless Assault 54 ~$3, Krenko, Mob Boss 52 ~$2) | `regular` | rarity sub-selectors — ≈ $36 nonfoil |
| tokens | 3 | `tddt` | `regular` | tokens |

**New art (local check, 6):** Aquitect's Will 2, Rootwater Hunter 16,
Streambed Aquitects 18, Tidal Courier 19, Island 30, Warren Instigator 32.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ddt = []` to enable `mm query missing-set ddt`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ddt = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Only the two face mythics are foil** (foil-only). Master of Waves 1 is a
  mythic here, ~$0.45.
- MTGJSON names the decks `Merfolk_DDT` and `Goblins_DDT`, typed `Duel Deck`,
  so they appear in `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ddt = []` — configured 2026-11-08 (enables `mm query missing-set ddt`).
- `config/families.toml` `[[unobtainable.ddt.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddt]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Merfolk vs. Goblins | Duel deck (MTGJSON `multiple_decks` / `duel`, plus two `deck` items) | Merfolk 1–31, Goblins 32–63 |

**Booster types (for `sealed-value` EV):** none.
