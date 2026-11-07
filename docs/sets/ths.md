# `ths` — Theros

> Per-family memory doc. Read this before answering set-specific questions about
> `ths` or working on `ths`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ths`
**Family root type:** `expansion`
**Family released:** 2013-09-27
**Last audit:** 2026-11-05 via `/characterize-set ths` (one-at-a-time run — tier decisions pending owner review).

---

> **First Theros set — Gods, Nykthos and the scry lands.** Theros-block pattern ([`ths`](ths.md) / [`bng`](bng.md) /
> [`jou`](jou.md)): base frame with the Nyx-starfield enchantment frame
> (`frame_effects` `enchantment`, cosmetic) on enchantment creatures and Gods;
> a promo set of **`N★` alt-art foils** (prerelease, release, buy-a-box) plus
> Game Day promos; and two in-store challenge-deck children, `tfth` and
> `thp1`, filed as `memorabilia`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ths` | expansion | 249 | 2013-09-27 | parent — booster set 1–249 (basics 230–249) |
| `pths` | promo | 10 | 2013-09-27 | prerelease `N★` (5, own art) + release 42★ + buy-a-box 180★ + Game Day (2) + Gift Box (1) |
| `tfth` | memorabilia | 15 | 2013-09-27 | *Face the Hydra* challenge deck (in-store; nonfoil, own art) |
| `thp1` | memorabilia | 7 | 2013-09-27 | *Hero's Path* (hero cards 1a–1e + 2, 3) |
| `tths` | token | 11 | 2013-09-27 | tokens |

`set:ths+related` covers all; master-list skips the two `memorabilia` children
by default.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 249 | `ths` 1–249 (121 C / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $178 nonfoil / $578 foil (Nykthos, Shrine to Nyx 223 ~$47 / $171, Purphoros 135 ~$25, Swan Song 65 ~$13 / $68, Erebos 85, Thoughtseize 107) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | **no — own art** | 5 `N★` foils (Celestial Archon 3★, Shipbreaker Kraken 63★, Abhorrent Overlord 75★, Ember Swallower 120★, Anthousa 149★) — but `missing.drop_datestamped_with_sibling` drops them (name + treatment match) |
| `release` + `datestamped` | — | **no** — own art, also dropped by that rule | Bident of Thassa 42★ |
| `gameday` | — | **no** — own art | Phalanx Leader 26, Nighthowler 98 (~$7) |
| `buyabox` | — | **no** — own art | Sylvan Caryatid 180★ (~$5) |
| `giftbox` | — | **no** — own art | Karametra's Acolyte 160 |
| `instore` | — | challenge-deck cards | `tfth`, `thp1` |

No Promo Pack, no fancy-foil sheet → proposed `[dupe_foil] ths = []` to enable
`mm query missing-set ths`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ths = []` | 0 | **apply** — empty, enables missing-set |
| `pths` promos | 10 | **owner's call** — all have their own art; the datestamped ones are hidden by missing-set today (a code question, see [`m15`](m15.md) §7) |
| `tfth` / `thp1` | 22 | already off by default (memorabilia) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pths` | prerelease / release / buy-a-box (alt art) | Sylvan Caryatid 180★ |
| plain CN | `pths` | Game Day / Gift Box | Nighthowler 98 |

---

## 7. Edge cases & gotchas

- **`★` CNs here are alt-art promos**, unlike the same-art resale `★` prints
  of later sets.
- **Prerelease packs are per-theme** (`prerelease-<theme>`, EV ~$6.58–$9.29).
- The challenge decks are cooperative "battle the AI deck" products; their
  cards aren't constructed-legal.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ths.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ths]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Event Deck | Event deck | — |
| *Face the Hydra* / Hero's Path | challenge deck (in-store) | `tfth` / `thp1` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ths --list-boosters` (2026-11-05): `draft` EV ~$4.34; `prerelease-<theme>` ~$6.58–$9.29.
