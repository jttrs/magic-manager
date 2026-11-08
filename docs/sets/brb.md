# `brb` — Battle Royale Box Set

> Per-family memory doc. Read this before answering set-specific questions about
> `brb` or working on `brb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `brb`
**Family root type:** `box`
**Family released:** 1999-11-12
**Last audit:** 2026-11-06 via `/characterize-set brb` (one-at-a-time run — tier decisions pending owner review).

---

> **Four-player multiplayer box (1999): four 40-card reprint decks**, nonfoil only. Standalone root, no tokens, no promos. 36 basics.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `brb` | box | 136 | 1999-11-12 | parent — deck cards 1–100, basics 101–136 |

No children. `box` isn't a default inventory set type, but the anchor is always included by `mm set master-list brb`.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| deck cards | 100 | `brb` 1–100 (60 C / 32 U / 8 R) | `regular` | rarity sub-selectors — ≈ $225 total incl. basics (Land Tax 35 ~$27 (uncommon), Reanimate 57 ~$24 (uncommon), Gorilla Warrior 30 ~$9, Windfall 99 ~$7; rares ≈ $31 — Catastrophe 12, Living Death 38, Wrath of God 100) |
| basics | 36 | `brb` 101–136 | `regular` | basics |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] brb = []` (2026-11-08) to enable `mm query missing-set brb`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] brb = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| whole family | 136 | **owner's call** — a reprint box (every print shares art with another local set); kept (default) — pending owner review |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **The valuable cards are uncommons** (Land Tax, Reanimate), invisible to the rare/mythic sub-selectors.
- MTGJSON: sealed product *Battle Royale Multi Player Box Set* (`multiple_decks` / `game_night`) and decks Chargoyf, Cinder Heart, Spirit Gale, The Deluge — typed `Theme Deck`, so not in `mm set precon-list`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] brb = []` — configured 2026-11-08 (enables `mm query missing-set brb`).
- `config/families.toml` `[[unobtainable.brb.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.brb]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Battle Royale box | box set (`multiple_decks` / `game_night`) | four 40-card decks |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py brb --list-boosters` (2026-11-06): none.
