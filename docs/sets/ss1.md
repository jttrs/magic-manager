# `ss1` — Signature Spellbook: Jace

> Per-family memory doc. Read this before answering set-specific questions about
> `ss1` or working on `ss1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ss1`
**Family root type:** `spellbook`
**Family released:** 2018-06-15
**Last audit:** 2026-11-05 via `/characterize-set ss1` (one-at-a-time run — tier decisions pending owner review).

---

> **The first Signature Spellbook:** eight blue reprints themed on Jace, in the
> Spellbook frame. Standalone (`parent_set_code: null`). Same shape as
> [`ss2`](ss2.md) and [`ss3`](ss3.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ss1` | spellbook | 8 | 2018-06-15 | parent — the only set, CN 1–8 |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Spellbook frame (foil + nonfoil) | 8 | `ss1` 1–8 (1 mythic, 7 rare; black border, `inverted`) | `b` | **every card computes `b`** from the `inverted` frame, though there is no plainer `ss1` print to prefer. Kept by default; the only print of each card in this family |

No `promo_types`, no `full_art`.

| CN | Name | Nonfoil / foil |
|---|---|---|
| 1 | Jace Beleren | ~$2.03 / ~$3.45 |
| 2 | Blue Elemental Blast | ~$1.83 / ~$8.82 |
| 3 | Brainstorm | ~$2.65 / ~$5.62 |
| 4 | Counterspell | ~$4.48 / ~$6.05 |
| 5 | Gifts Ungiven | ~$4.52 / ~$6.97 |
| 6 | Mystical Tutor | ~$17.83 / ~$21.53 |
| 7 | Negate | ~$0.46 / ~$1.45 |
| 8 | Threads of Disloyalty | ~$0.30 / ~$0.47 |

Totals ≈ $34 nonfoil / $54 foil.

**Art reuse:** Jace Beleren 1 reuses its `m10` art (also on `m11`, `cmm`,
`mb2`) and Counterspell 4 reuses its `dd2` art (also on `jvc`, `cmm`). The other
six have new art; later reprints reuse three of them (Brainstorm on `plst` and
`frc`, Gifts Ungiven on `2x2`, Mystical Tutor on `plst`).

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ss1 = []` to enable `mm query missing-set ss1`.

---

## 3. Chase variants

Mystical Tutor 6 carries most of the value.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ss1 = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Everything computes `b`:** the Spellbook frame is `inverted`, so a
  treatment filter that drops `b` empties the set. Same as `ss2`/`ss3`.
- **The rarity is the Spellbook's, not the card's original:** Brainstorm and
  Counterspell are rare here.
- Shared art means an `illustration_id` search for Jace Beleren or Counterspell
  also returns their older printings.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ss1 = []` — configured 2026-11-08 (enables `mm query missing-set ss1`).
- `config/families.toml` `[[unobtainable.ss1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ss1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Signature Spellbook: Jace | box set (MTGJSON `box_set` / `spellbook`; decklist `SignatureSpellbookJace_SS1`, `type: Box Set`) | 8 cards, fixed contents |

**Booster types (for `sealed-value` EV):** none.
