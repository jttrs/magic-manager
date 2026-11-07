# `dgm` — Dragon's Maze

> Per-family memory doc. Read this before answering set-specific questions about
> `dgm` or working on `dgm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dgm`
**Family root type:** `expansion`
**Family released:** 2013-05-03
**Last audit:** 2026-11-05 via `/characterize-set dgm` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Return to Ravnica set — a small set (156) with a guildgate land
> slot**, base frame only. Promo set of `N★` alt-art foils, including a
> prerelease **Plains `157★`** (a CN beyond the set — DGM has no basics).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dgm` | expansion | 156 | 2013-05-03 | parent — CN 1–156 (Cluestones ~136–145, guildgates 146–156 incl. Maze's End 152) |
| `pdgm` | promo | 6 | 2013-05-03 | prerelease Maze's End `152★` + Plains `157★`, release Breaking // Entering `124★`, buy-a-box Render Silent `96★` (~$9.63), Game Day Melek 84 / Trostani's Summoner 110 |
| `tdgm` | token | 1 | 2013-05-03 | token |

`set:dgm+related` covers all three.

---

## 2. Treatments

Every print computes `regular`. No `frame_effects`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 156 | `dgm` 1–156 (70 C / 40 U / 35 R / 11 M) | `regular` | rarity/base sub-selectors — R+M ≈ $28 nonfoil / $184 foil (Master of Cruelties 82 ~$5, Render Silent 96 ~$35 foil, Voice of Resurgence 114 ~$19 foil, Progenitor Mimic 92) |

**`promo_types`:** every `pdgm` print has its own art. The two prerelease and
the release promo carry `datestamped`, so `missing.drop_datestamped_with_sibling`
drops Maze's End `152★` and Breaking // Entering `124★` (Plains `157★` has
no `dgm` sibling, so it stays). Proposed `[dupe_foil] dgm = []`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dgm = []` | 0 | **apply** — empty, enables missing-set |
| `pdgm` promos | 6 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `152★`, `157★` | `pdgm` | prerelease (alt art) | Plains `157★` |
| `124★` / `96★` | `pdgm` | release / Buy-a-Box | Render Silent `96★` |
| `84`, `110` | `pdgm` | Game Day | Melek, Izzet Paragon 84 |

---

## 7. Edge cases & gotchas

- **No basics in `dgm`**; the only "DGM" basic is the prerelease Plains
  `157★`. The booster land slot (MTGJSON sheet `land`, 21 cards) is the 10
  guildgates + Maze's End **plus the 10 shocklands from `rtr`/`gtc`** — so a
  DGM pack can contain a card from another family.
- **Huge foil premium** on a cheap set (R+M ~$28 nonfoil vs ~$184 foil).
- MTGJSON lists a `six` booster type besides `draft` — not a retail pack.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.dgm.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.dgm]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | land slot: guildgates, Maze's End or an RTR/GTC shockland |
| Intro Packs ×5 / Event Deck *Strength of Selesnya* | Intro pack / Event deck | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dgm --list-boosters` (2026-11-05): `draft` EV ~$2.97, 94% coverage.
