# `frf` — Fate Reforged

> Per-family memory doc. Read this before answering set-specific questions about
> `frf` or working on `frf`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `frf`
**Family root type:** `expansion`
**Family released:** 2015-01-23
**Last audit:** 2026-11-05 via `/characterize-set frf` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Khans block set, base frame only**, with two quirks: six rares are
> split by finish into **nonfoil N and foil N★ rows with the same art**, and
> the family holds **Ugin's Fate** (`ugin`), 26 nonfoil alt-art promos. Also a
> Clash Pack (`cp2`), Intro Pack foils and event promos.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `frf` | expansion | 191 | 2015-01-23 | parent — booster set 1–185 (basics 176–185) + six `N★` foil rows |
| `pfrf` | promo | 43 | 2015-01-23 | prerelease `Ns` datestamped (30) + Promo Pack `Np` stamped (3) + Intro Pack foils (5) + game day / release / buy-a-box / resale (5) |
| `ugin` | promo | 26 | 2015-01-17 | Ugin's Fate — nonfoil alt-art promos (Ugin, the Spirit Dragon 1 ~$40, Altar of the Brood 216 ~$28, Grim Haruspex 73 ~$12) |
| `cp2` | starter | 6 | 2015-01-23 | Fate Reforged Clash Pack — 6 foil alt-art cards (Whip of Erebos 5 ~$18) |
| `tfrf` | token | 4 | 2015-01-23 | tokens |

`set:frf+related` covers all five.

---

## 2. Treatments

Every print computes `regular`. `cp2`'s `enchantment` frame effect is cosmetic.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 185 | `frf` 1–185 (80 C / 60 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $42 nonfoil / $134 foil (Ugin, the Spirit Dragon 1 ~$16, Temporal Trespass 55, Dark Deal 66) |
| **finish-split rares** | 6 + 6 | `frf` 8, 43, 65, 79, 110, 131 (nonfoil-only) and `8★`, `43★`, `65★`, `79★`, `110★`, `131★` (foil-only, **same art**) — the five Sieges + Crux of Fate | `regular` | **one card, two rows**: the foil booster sheet uses the ★ rows. The ★ rows are unpriced locally |
| Ugin's Fate | 26 | `ugin` (nonfoil, own art) | `regular` | rarity sub-selectors — ≈ $96 |
| Clash Pack | 6 | `cp2` 1–6 (foil, own art) | `regular` | ≈ $22 |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 30 prints, auto-dropped (~$105 foil) |
| `promopack` + `stamped` | `regular` | **yes** | 3 prints, ~$16 / $34 |
| `intropack` | — | **no** — own art | 5 foil rares (Archfiend of Depravity 62 ~$15, Dragonscale General 11, …) |
| `gameday` / `release` / `buyabox` | — | **no** — own art | Supplant Form 54 (~$10), Mardu Shadowspear 74, Sandsteppe Mastodon 137, Shamanic Revelation 138 |
| `resale` | — | same art | Atarka `149★` |
| `setpromo` (`ugin`) | — | **no** — own art | marker on every Ugin's Fate card |

No fancy-foil sheet → proposed `[dupe_foil] frf = []` to enable `mm query missing-set frf`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] frf = []` | 0 | **apply** — empty, enables missing-set |
| `pfrf` promo-pack stamped `Np` | 3 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$16 |
| `pfrf` Intro Pack foils + event promos | 10 | **owner's call** — 9 have their own art |
| `ugin` Ugin's Fate | 26 | **owner's call** — alt-art promos from the FRF prerelease/launch event; real cards, ~$96 |
| `cp2` Clash Pack | 6 | keep — own art |
| `N★` foil rows | 6 | keep — they are the foils of those cards |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `Np` | `pfrf` | prerelease / Promo Pack | — |
| `11`, `50`, `62`, `99`, `142` | `pfrf` | Intro Pack foil (alt art) | Archfiend of Depravity 62 |
| `54`, `74` | `pfrf` | Game Day | Supplant Form 54 |
| `137` / `138` | `pfrf` | Release / Buy-a-Box | Shamanic Revelation 138 |
| `149★` | `pfrf` | resale | Atarka, World Render |
| various | `ugin` | Ugin's Fate | Ugin, the Spirit Dragon 1 |
| `1`–`6` | `cp2` | Clash Pack *Power and Profit* | Whip of Erebos 5 |

---

## 7. Edge cases & gotchas

- **Foil Crux of Fate is `65★`, not a foil of 65.** Recording a foil copy
  against `frf` 65 targets a finish that doesn't exist; the `★` rows are
  foil-only, the plain rows nonfoil-only (same illustration).
- **`ugin` is a separate promo set** with its own CNs taken from the Khans
  block (Ugin 1, Altar of the Brood 216) — not FRF CNs.
- **Prerelease packs are per-clan** (`prerelease-<clan>`, EV ~$2.81–$6.53).
- Sandsteppe Mastodon 137 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.frf.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.frf]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | ★ foils on the foil sheet |
| Intro Packs ×5 | Intro pack | each with a foil `pfrf` rare |
| Clash Pack *Power and Profit* | Clash pack | `cp2` |
| Fat Pack | Bundle | Fat Pack Land Pack (pool) |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py frf --list-boosters` (2026-11-05): `draft` EV ~$3.38; `prerelease-<clan>` ~$2.81–$6.53.
