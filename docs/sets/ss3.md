# `ss3` — Signature Spellbook: Chandra

> Per-family memory doc. Read this before answering set-specific questions about
> `ss3` or working on `ss3`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ss3`
**Family root type:** `spellbook`
**Family released:** 2020-06-26
**Last audit:** 2026-11-04 via `/characterize-set ss3` (one-at-a-time run — tier decisions pending owner review).

---

> **A fixed-content 8-card box.** The third (and, so far, last) Signature
> Spellbook: Chandra plus 7 red spells, all in the inverted ("Spellbook") frame,
> foil and nonfoil. Standalone (`parent_set_code: null`).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ss3` | spellbook | 8 | 2020-06-26 | parent — the only set, CN 1–8 |

No children. No `--only` needed.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Spellbook frame (foil + nonfoil) | 8 | `ss3` 1–8 (2 mythic, 6 rare; black border, `inverted`) | `b` | handled by the `preferred` class — **every card computes `b`** from the `inverted` frame, though there is no plainer `ss3` print to prefer. Kept by default; the only print of each card in this family |

Security stamp `circle` on all 8. No `promo_types`, no `full_art`.

**Art is NOT always new.** 4 of 8 reuse an earlier illustration: Chandra,
Torch of Defiance 1 (KLD 110), Cathartic Reunion 2 (KLD 109), Young Pyromancer 8
(M14 163, the most-reprinted art here); Rite of Flame 7's art appears only on its
List reprint `plst` SS3-7.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

| CN | Name | Artist |
|---|---|---|
| 1 | Chandra, Torch of Defiance | Magali Villeneuve |
| 2 | Cathartic Reunion | Howard Lyon |
| 3 | Fiery Confluence | Micah Epstein |
| 4 | Past in Flames | Josu Hernaiz |
| 5 | Pyroblast | Yongjae Choi |
| 6 | Pyromancer Ascension | Karl Kopinski |
| 7 | Rite of Flame | Kieran Yanner |
| 8 | Young Pyromancer | Cynthia Sheppard |

---

## 5. Unobtainable rules

No rule is active; none needed. Configured `[dupe_foil] ss3 = []` (2026-11-08) only to enable
`mm query missing-set ss3`.

**Totals (local prices, 2026-11-04):** ≈ $25 nonfoil / $68 foil (Pyroblast 5
~$11 / ~$30, Rite of Flame 7 ~$6 / ~$21 lead).

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Computes `b` without being borderless** — black border, `inverted` frame
  effect. Same pattern as the Heroes-of-the-Realm land in [`ph20`](ph20.md).
- Every card exists in both finishes; foil roughly 2–3× nonfoil.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ss3 = []` — configured 2026-11-08 (enables `mm query missing-set ss3`).
- `config/families.toml` `[[unobtainable.ss3.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ss3]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Signature Spellbook: Chandra | box set (MTGJSON `sealedProduct`) | 8 cards, fixed contents |

**Booster types (for `sealed-value` EV):** none.
