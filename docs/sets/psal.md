# `psal` — Salvat 2005

> Per-family memory doc. Read this before answering set-specific questions about
> `psal` or working on `psal`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `psal`
**Family root type:** `box`
**Family released:** 2005-08-22
**Last audit:** 2026-11-06 via `/characterize-set psal` (one-at-a-time run — tier decisions pending owner review).

---

> **Twelve 60-card tribal decks from a Salvat magazine partwork, printed only in Spanish (decks A–J) and Italian (K–L). Standalone root. Like `ps11`, it cannot be synced: `mm set sync` keeps English cards only, so the family is empty locally.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `psal` | box | 720 (Scryfall) / 0 local | 2005-08-22 | parent — decks A–L, 60 cards each, CN `<letter><n>` (A1–A60 … L1–L60) |

The anchor is always included by `mm set master-list psal`, whatever its
`set_type`.

---

## 2. Treatments

All nonfoil, no `frame_effects` (data from live Scryfall, 2026-11-06).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| Spanish decks | 600 | `psal` A–J | `regular` | n/a locally |
| Italian decks | 120 | `psal` K–L | `regular` | n/a locally |
| (all) | 720 | 503 C / 157 U / 60 R | — | only 14 prints priced, ≈ $296 total (Lightning Greaves L2 ~$150, Soul Warden J14 ~$19, Marrow-Gnawer A1 ~$18) |

**New art (local check):** n/a — nothing local; the decks reprint existing cards. Configured `[dupe_foil] psal = []` (2026-11-08) to enable
`mm query missing-set psal`.

---

## 3–6.

No chase variants, scenes or PRM destinations. Unobtainable rules: no rule is active; `[dupe_foil] psal = []` —
**applied 2026-11-08**. Whole family (720) — **owner's call**: non-English partwork, not syncable; kept (default) — pending owner review.

---

## 7. Edge cases & gotchas

- **Non-English only**, so the local catalog has none of it and `mm query missing-set psal` returns nothing. Same code gap as `ps11`.
- MTGJSON lists the 12 decks as `Theme Deck`s: Angels, Beasts, Berserk, Cats, Elves, Ninjas, Ravenous Rats, Slivers, Spirits, Thallids, Wizards, Zombies (not in `PRECON_MODERN_TYPES`).
- CNs are letter-prefixed by deck.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] psal = []` — configured 2026-11-08 (enables `mm query missing-set psal`).
- `config/families.toml` `[[unobtainable.psal.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.psal]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Salvat partwork decks ×12 | magazine partwork | one 60-card tribal deck per issue |

**Booster types (for `sealed-value` EV):** none.
