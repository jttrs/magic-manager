# `dtk` — Dragons of Tarkir

> Per-family memory doc. Read this before answering set-specific questions about
> `dtk` or working on `dtk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `dtk`
**Family root type:** `expansion`
**Family released:** 2015-03-27
**Last audit:** 2026-11-05 via `/characterize-set dtk` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Khans block set, base frame only.** Intro Packs with alt-art foil
> rares, a few event promos, and the *Tarkir Dragonfury* in-store promos
> (`ptkdf`). No Planeswalker Decks.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `dtk` | expansion | 264 | 2015-03-27 | parent — booster set 1–264 (basics 250–264) |
| `pdtk` | promo | 51 | 2015-03-27 | prerelease `Ns` datestamped (40) + Promo Pack `Np` stamped (2) + Intro Pack foils (5) + game day / release / buy-a-box (4) |
| `ptkdf` | promo | 4 | 2015-04-03 | Tarkir Dragonfury in-store promos (nonfoil, own art) |
| `tdtk` | token | 8 | 2015-03-27 | tokens |

`set:dtk+related` covers all four.

---

## 2. Treatments

Every print computes `regular`. No `frame_effects`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 264 | `dtk` 1–264 (116 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $99 nonfoil / $331 foil (Sarkhan Unbroken 230 ~$19, Dragonlord Kolaghan 218 ~$13, Sidisi 120 ~$9, Narset 225, Shaman of Forgotten Ways 204 ~$30 foil) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 40 prints, auto-dropped (~$130 foil) |
| `promopack` + `stamped` | `regular` | **yes** | 2 prints (Sidisi `120p`, …), ~$31 / $60 |
| `intropack` | — | **no** — own art | 5 foil rares (Arashin Sovereign 212, Boltwing Marauder 214, Harbinger of the Hunt 223, Necromaster Dragon 226, Pristine Skywise 228) |
| `gameday` / `release` / `buyabox` | — | **no** — own art | Thunderbreak Regent 162 (~$5), Scaleguard Sentinels 201, Deathbringer Regent 96, Ojutai's Command 227 |
| `instore` (`ptkdf`) | — | **no** — own art | Dragon Fodder 135, Dragonlord's Servant 138, Foe-Razer Regent 187, Evolving Wilds 248 |

No fancy-foil sheet → configured `[dupe_foil] dtk = []` (2026-11-08) to enable `mm query missing-set dtk`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] dtk = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pdtk` promo-pack stamped `Np` | 2 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$31 |
| `pdtk` Intro Pack foils + event promos, `ptkdf` | 13 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `Np` | `pdtk` | prerelease / Promo Pack | Sidisi `120p` |
| `212`, `214`, `223`, `226`, `228` | `pdtk` | Intro Pack foil (alt art) | Harbinger of the Hunt 223 |
| `162`, `201` | `pdtk` | Game Day | Thunderbreak Regent 162 |
| `96` / `227` | `pdtk` | Release / Buy-a-Box | Ojutai's Command 227 |
| `135`, `138`, `187`, `248` | `ptkdf` | Tarkir Dragonfury (in-store) | Foe-Razer Regent 187 |

---

## 7. Edge cases & gotchas

- **Prerelease packs are per-dragonlord clan** (`prerelease-<clan>` booster
  types, EV ~$2.60–$6.31); MTGJSON also has a `fat-pack` booster type.
- Deathbringer Regent 96 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).
- MTGJSON's Event Deck *Landslide Charge* is typed `Event Deck`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] dtk = []` — configured 2026-11-08 (enables `mm query missing-set dtk`).
- `config/families.toml` `[[unobtainable.dtk.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.dtk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | each with a foil `pdtk` rare |
| Event Deck *Landslide Charge* | Event deck | — |
| Fat Pack | Bundle | Fat Pack Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py dtk --list-boosters` (2026-11-05): `draft` EV ~$3.18; `prerelease-<clan>` ~$2.60–$6.31; `fat-pack` ~$1.45.
