# `rtr` — Return to Ravnica

> Per-family memory doc. Read this before answering set-specific questions about
> `rtr` or working on `rtr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `rtr`
**Family root type:** `expansion`
**Family released:** 2012-10-05
**Last audit:** 2026-11-05 via `/characterize-set rtr` (one-at-a-time run — tier decisions pending owner review).

---

> **First Return to Ravnica set — five guilds and the return of their five shocklands.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `rtr` | expansion | 274 | 2012-10-05 | parent — booster set 1–274 (shocklands 237–248, basics 250–274) |
| `prtr` | promo | 10 | 2012-10-05 | prerelease `N★` (5) + release Deadbridge Goliath `120★` + buy-a-box Supreme Verdict `201★` + Gift Box Dreg Mangler 158 + Game Day Cryptborn Horror 212 / Dryad Militant 214 |
| `trtr` | token | 12 | 2012-10-05 | tokens |

`set:rtr+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 274 | `rtr` 1–274 (126 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $141 nonfoil / $419 foil (Cyclonic Rift 35 ~$31, Utvara Hellkite 110 ~$13, Steam Vents 247 ~$11, Blood Crypt 238 ~$10, Deathrite Shaman 213 ~$8 / $36) |

**`promo_types`:** every `prtr` print has its own art (Supreme Verdict `201★` ~$4.93). The prerelease and release promos carry
`datestamped`, so `missing.drop_datestamped_with_sibling` drops them from
missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] rtr = []` (2026-11-08) to enable `mm query missing-set rtr`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] rtr = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `prtr` promos | 10 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `prtr` | prerelease / release / Buy-a-Box (alt art) | Supreme Verdict `201★` |
| `158` | `prtr` | Gift Box (alt art) | Dreg Mangler |
| `212`, `214` | `prtr` | Game Day | Cryptborn Horror 212 |

---

## 7. Edge cases & gotchas

- **Prerelease packs are per-guild** (`prerelease-<guild>`, EV ~$3.37–$5.33); MTGJSON also lists a `six` booster type (not retail).
- The five RTR guilds' shocklands are here; the other five are in [`gtc`](gtc.md), and both sets' shocks also appear in [`dgm`](dgm.md) boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] rtr = []` — configured 2026-11-08 (enables `mm query missing-set rtr`).
- `config/families.toml` `[[unobtainable.rtr.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.rtr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 / Event Decks ×2 / Welcome Decks ×5 | Intro pack / Event deck / Welcome deck | Event Decks: Creep and Conquer, Wrack and Rage |
| Booster Battle Pack | two-player pack | — |
| Fat Pack / Holiday Gift Box | Bundle / gift bundle | `prtr` 158 in the Gift Box |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py rtr --list-boosters` (2026-11-05): `draft` EV ~$4.69; `prerelease-<guild>` ~$3.37–$5.33.
