# `bng` — Born of the Gods

> Per-family memory doc. Read this before answering set-specific questions about
> `bng` or working on `bng`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `bng`
**Family root type:** `expansion`
**Family released:** 2014-02-07
**Last audit:** 2026-11-05 via `/characterize-set bng` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Theros set — five more Gods, Brimaz, Kiora.** Theros-block pattern ([`ths`](ths.md) / [`bng`](bng.md) /
> [`jou`](jou.md)): base frame with the Nyx-starfield enchantment frame
> (`frame_effects` `enchantment`, cosmetic) on enchantment creatures and Gods;
> a promo set of **`N★` alt-art foils** (prerelease, release, buy-a-box) plus
> Game Day promos; and two in-store challenge-deck children, `tbth` and
> `thp2`, filed as `memorabilia`.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `bng` | expansion | 165 | 2014-02-07 | parent — booster set 1–165 (no basics — boosters used Theros basics) |
| `pbng` | promo | 9 | 2014-02-07 | prerelease `N★` (5, own art) + release 55★ + buy-a-box 94★ + Game Day (2) |
| `tbth` | memorabilia | 15 | 2014-02-07 | *Battle the Horde* challenge deck (in-store; nonfoil, own art) |
| `thp2` | memorabilia | 7 | 2014-02-07 | *Hero's Path* (hero cards 4a–4e + 5, 6) |
| `tbng` | token | 11 | 2014-02-07 | tokens |

`set:bng+related` covers all; master-list skips the two `memorabilia` children
by default.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 165 | `bng` 1–165 (60 C / 60 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $71 nonfoil / $273 foil (Phenax 152 ~$13, Brimaz 5 ~$10, Xenagos 156 ~$10, Ephara 145 ~$7 / $33) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | **no — own art** | 5 `N★` foils (Silent Sentinel 26★, Arbiter of the Ideal 31★, Eater of Hope 66★, Forgestoker Dragon 98★, Nessian Wilds Ravager 129★) — but `missing.drop_datestamped_with_sibling` drops them (name + treatment match) |
| `release` + `datestamped` | — | **no** — own art, also dropped by that rule | Tromokratis 55★ |
| `gameday` | — | **no** — own art | Pain Seer 80, Kiora's Follower 150 (~$4) |
| `buyabox` | — | **no** — own art | Fated Conflagration 94★ |
| `instore` | — | challenge-deck cards | `tbth`, `thp2` |

No Promo Pack, no fancy-foil sheet → proposed `[dupe_foil] bng = []` to enable
`mm query missing-set bng`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] bng = []` | 0 | **apply** — empty, enables missing-set |
| `pbng` promos | 9 | **owner's call** — all have their own art; the datestamped ones are hidden by missing-set today (a code question, see [`m15`](m15.md) §7) |
| `tbth` / `thp2` | 22 | already off by default (memorabilia) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pbng` | prerelease / release / buy-a-box (alt art) | Fated Conflagration 94★ |
| plain CN | `pbng` | Game Day | Kiora's Follower 150 |

---

## 7. Edge cases & gotchas

- **`★` CNs here are alt-art promos**, unlike the same-art resale `★` prints
  of later sets.
- **No basics** in the set.
- **Prerelease packs are per-theme** (`prerelease-<theme>`, EV ~$2.83–$4.16).
- The challenge decks are cooperative "battle the AI deck" products; their
  cards aren't constructed-legal.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.bng.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.bng]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Event Deck | Event deck | — |
| *Battle the Horde* / Hero's Path | challenge deck (in-store) | `tbth` / `thp2` |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py bng --list-boosters` (2026-11-05): `draft` EV ~$3.71; `prerelease-<theme>` ~$2.83–$4.16.
