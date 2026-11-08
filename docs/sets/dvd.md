# `dvd` — Duel Decks Anthology: Divine vs. Demonic

> Per-family memory doc. Read this before answering set-specific questions about
> `dvd` or working on `dvd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `dvd`
**Family root type:** `duel_deck`
**Family released:** 2014-12-05
**Last audit:** 2026-11-05 via `/characterize-set dvd` (one-at-a-time run — tier decisions pending owner review).

---

> **A 2014 reprint of the 2009 Duel Deck [`ddc`](ddc.md)**, one of four
> decks pairs in the *Duel Decks Anthology* box ([`jvc`](jvc.md),
> [`gvl`](gvl.md), [`evg`](evg.md), [`dvd`](dvd.md)). Every print reuses the
> original's art. Standalone root.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dvd` | duel_deck | 62 | 2014-12-05 | parent — Divine deck 1–29, Demonic deck 30–62 |
| `tdvd` | token | 3 | 2014-12-05 | tokens |

`duel_deck` isn't a default inventory set type, but the anchor is always
included by `mm set master-list dvd`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| face cards (**foil-only**, mythic) | 2 | `dvd` 1 Akroma, Angel of Wrath, 30 Lord of the Pit | `regular` | mythic-regular — ~$5.30 foil |
| deck cards (nonfoil-only) | 60 | the rest (Demonic Tutor 49 ~$75, Dark Ritual 45 ~$5, Reya Dawnbringer 13) | `regular` | rarity sub-selectors — ≈ $109 |
| tokens | 3 | `tdvd` | `regular` | tokens |

**Art:** 0 new — every print shares its illustration with the original
`ddc` (or an earlier printing).

Configured `[dupe_foil] dvd = []` (2026-11-08) to enable `mm query missing-set dvd`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] dvd = []` —
**applied 2026-11-08**.

---

## 7. Edge cases & gotchas

- **Same cards and art as `ddc`**, different set code and frame year — a
  "missing from `dvd`" list is a list of reprint printings.
- **Only the two face cards are foil** (foil-only), as in the original.
- MTGJSON decks `Divine` / `Demonic` (`type: Duel Deck`); the Anthology box itself
  isn't a separate MTGJSON product — each set lists its two decks.
- **Demonic Tutor 49 (~$75) is most of the value**, rated uncommon here.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dvd = []` — configured 2026-11-08 (enables `mm query missing-set dvd`).
- `config/families.toml` `[[unobtainable.dvd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dvd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Duel Decks Anthology (box of 4 pairs) | Duel deck | Divine 1–29, Demonic 30–62 |

**Booster types (for `sealed-value` EV):** none.
