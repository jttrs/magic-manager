# `jou` — Journey into Nyx

> Per-family memory doc. Read this before answering set-specific questions about
> `jou` or working on `jou`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `jou`
**Family root type:** `expansion`
**Family released:** 2014-05-02
**Last audit:** 2026-11-05 via `/characterize-set jou` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Theros set — the last five Gods and Mana Confluence.** Theros-block pattern ([`ths`](ths.md) / [`bng`](bng.md) /
> [`jou`](jou.md)): base frame with the Nyx-starfield enchantment frame
> (`frame_effects` `enchantment`, cosmetic) on enchantment creatures and Gods;
> a promo set of **`N★` alt-art foils** (prerelease, release, buy-a-box) plus
> Game Day promos; and two in-store challenge-deck children, `tdag` and
> `thp3`, filed as `memorabilia`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `jou` | expansion | 165 | 2014-05-02 | parent — booster set 1–165 (no basics — boosters used Theros basics) |
| `pjou` | promo | 10 | 2014-05-02 | prerelease `N★` (5, own art) + release 93★ + buy-a-box 122★ + Game Day (3) |
| `tdag` | memorabilia | 15 | 2014-05-02 | *Defeat a God* challenge deck (in-store; nonfoil, own art) |
| `thp3` | memorabilia | 8 | 2014-05-02 | *Hero's Path* (hero weapons 7a–7e + 8, 9) |
| `tjou` | token | 6 | 2014-05-02 | tokens |

`set:jou+related` covers all; master-list skips the two `memorabilia` children
by default.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `jou` 1–165 (60 C / 60 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $140 nonfoil / $445 foil (Mana Confluence 163 ~$34, Dictate of Erebos 65 ~$17, Athreos 146 ~$14 / $42, Sage of Hours 50 ~$12 / $56, Iroas 150) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | **no — own art** | 5 `N★` foils (Dawnbringer Charioteers 6★, Scourge of Fleets 51★, Doomwake Giant 66★, Spawn of Thraxes 112★, Heroes' Bane 126★) — but `missing.drop_datestamped_with_sibling` drops them (name + treatment match) |
| `release` + `datestamped` | — | **no** — own art, also dropped by that rule | Dictate of the Twin Gods 93★ (~$3.64) |
| `gameday` | — | **no** — own art | Dictate of Kruphix 37 (~$8), Squelching Leeches 84, Hall of Triumph 162 |
| `buyabox` | — | **no** — own art | Eidolon of Blossoms 122★ (~$5) |
| `instore` | — | challenge-deck cards | `tdag`, `thp3` |

No Promo Pack, no fancy-foil sheet → proposed `[dupe_foil] jou = []` to enable
`mm query missing-set jou`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] jou = []` | 0 | **apply** — empty, enables missing-set |
| `pjou` promos | 10 | **owner's call** — all have their own art; the datestamped ones are hidden by missing-set today (a code question, see [`m15`](m15.md) §7) |
| `tdag` / `thp3` | 23 | already off by default (memorabilia) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pjou` | prerelease / release / buy-a-box (alt art) | Eidolon of Blossoms 122★ |
| plain CN | `pjou` | Game Day | Dictate of Kruphix 37 |

---

## 7. Edge cases & gotchas

- **`★` CNs here are alt-art promos**, unlike the same-art resale `★` prints
  of later sets.
- **No basics** in the set.
- **Prerelease packs are per-theme** (`prerelease-<theme>`, EV ~$6.33–$10.89).
- The challenge decks are cooperative "battle the AI deck" products; their
  cards aren't constructed-legal.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.jou.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.jou]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Event Deck | Event deck | — |
| *Defeat a God* / Hero's Path | challenge deck (in-store) | `tdag` / `thp3` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py jou --list-boosters` (2026-11-05): `draft` EV ~$4.96; `prerelease-<theme>` ~$6.33–$10.89.
