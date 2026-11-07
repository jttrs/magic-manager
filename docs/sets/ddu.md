# `ddu` — Duel Decks: Elves vs. Inventors

> Per-family memory doc. Read this before answering set-specific questions about
> `ddu` or working on `ddu`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ddu`
**Family root type:** `duel_deck`
**Family released:** 2018-04-06
**Last audit:** 2026-11-05 via `/characterize-set ddu` (one-at-a-time run — tier decisions pending owner review).

---

> **The last Duel Decks product:** two 60-card reprint decks, each led by a
> foil-only mythic. Standalone root (`parent_set_code: null`). Base frame
> only. Four cards have art not seen in any other set.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ddu` | duel_deck | 76 | 2018-04-06 | parent — Elves deck 1–34 (Woodland Warriors, basics 31–34), Inventors deck 35–76 (Ingenious Machinists) |
| `tddu` | token | 4 | 2018-04-06 | tokens |

`set:ddu+related` covers both. `duel_deck` isn't a default inventory set type,
but the anchor is always included by `mm set master-list ddu`.

---

## 2. Treatments

All `regular`. `frame_effects` `legendary` is cosmetic. No `promo_types`, no
`full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `ddu` 1 Ezuri, Renegade Leader (~$22), 35 Goblin Welder (~$22) | `regular` | mythic-regular — both have new art |
| deck cards (nonfoil-only) | 74 | `ddu` 2–34, 36–76 (16 rares; Darksteel Plate 52 ~$5, Regal Force 22 ~$4) | `regular` | rarity sub-selectors — ≈ $41 nonfoil for all 74 |
| tokens | 4 | `tddu` | `regular` | tokens |

Rarity totals (`ddu`): 39 C / 19 U / 16 R / 2 M.

**New art (4):** Ezuri 1, Elvish Branchbender 6, Regal Force 22, Goblin Welder
35. Every other card reuses an earlier illustration. (Local-catalog check; an
unsynced original set can make a reprint look new.)

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ddu = []` to enable `mm query missing-set ddu`.

---

## 3. Chase variants

None. The two foil mythics carry half the set's value.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ddu = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Only the two face mythics are foil** (foil-only); everything else is
  nonfoil-only. A foil Regal Force doesn't exist in this set.
- MTGJSON names the decks *Woodland Warriors* (`WoodlandWarriors_DDU`) and
  *Ingenious Machinists* (`IngeniousMachinists_DDU`), typed `Duel Deck`, so
  they appear in `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ddu.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ddu]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks: Elves vs. Inventors | Duel deck (MTGJSON `multiple_decks` / `duel`, plus two `deck` items) | Woodland Warriors 1–34, Ingenious Machinists 35–76 |

**Booster types (for `sealed-value` EV):** none.
