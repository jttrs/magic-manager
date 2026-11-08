# `ss2` — Signature Spellbook: Gideon

> Per-family memory doc. Read this before answering set-specific questions about
> `ss2` or working on `ss2`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ss2`
**Family root type:** `spellbook`
**Family released:** 2019-06-28
**Last audit:** 2026-11-05 via `/characterize-set ss2` (one-at-a-time run — tier decisions pending owner review).

---

> **A fixed-content 8-card box.** The second Signature Spellbook: Gideon Jura
> plus 7 white spells, all in the inverted ("Spellbook") frame, foil and
> nonfoil. Standalone (`parent_set_code: null`). Same shape as [`ss3`](ss3.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ss2` | spellbook | 8 | 2019-06-28 | parent — the only set, CN 1–8 |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Spellbook frame (foil + nonfoil) | 8 | `ss2` 1–8 (1 mythic, 7 rare; black border, `inverted`; Blackblade Reforged 8 also `legendary`) | `b` | **every card computes `b`** from the `inverted` frame, though there is no plainer `ss2` print to prefer. Kept by default; the only print of each card in this family |

Security stamp `circle` on all 8. No `promo_types`, no `full_art`.

| CN | Name | Nonfoil / foil |
|---|---|---|
| 1 | Gideon Jura | ~$0.40 / ~$1.08 |
| 2 | Martyr's Bond | ~$0.45 / ~$1.37 |
| 3 | Path to Exile | ~$2.11 / ~$4.45 |
| 4 | Rest in Peace | ~$1.50 / ~$1.51 |
| 5 | Shielded by Faith | ~$2.39 / ~$5.66 |
| 6 | True Conviction | ~$5.62 / ~$9.28 |
| 7 | Worship | ~$0.47 / ~$3.19 |
| 8 | Blackblade Reforged | ~$5.23 / ~$17.94 |

**Art reuse:** only Gideon Jura 1 reuses an earlier illustration (ROE 21, also
on M12 16). True Conviction 6's art later reappears on `scd` 38; Rest in Peace 4
and Blackblade Reforged 8 reappear on their List reprints `plst` SS2-4 / SS2-8.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

No rule is active; none needed. Configured `[dupe_foil] ss2 = []` (2026-11-08) only to enable
`mm query missing-set ss2`.

**Totals (local prices, 2026-11-05):** ≈ $18 nonfoil / $45 foil.

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Computes `b` without being borderless** — black border, `inverted` frame
  effect. Same as [`ss3`](ss3.md).
- **The List reprints (`plst` SS2-n) share the Spellbook art**, so a "same art"
  check against `plst` finds a match without implying a dupe inside `ss2`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ss2 = []` — configured 2026-11-08 (enables `mm query missing-set ss2`).
- `config/families.toml` `[[unobtainable.ss2.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ss2]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Signature Spellbook: Gideon | box set (MTGJSON `box_set` / `spellbook`) | 8 cards, fixed contents |

**Booster types (for `sealed-value` EV):** none.
