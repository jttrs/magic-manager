# `ktk` — Khans of Tarkir

> Per-family memory doc. Read this before answering set-specific questions about
> `ktk` or working on `ktk`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ktk`
**Family root type:** `expansion`
**Family released:** 2014-09-26
**Last audit:** 2026-11-05 via `/characterize-set ktk` (one-at-a-time run — tier decisions pending owner review).

---

> **Wedge-clan expansion with the enemy fetchlands, base frame only** — plus a
> trap: **24 Arena-only `y` prints** (Scryfall `availability: arena`, released
> 2023-12-12) sit in `ktk` itself, carry no `arena` security stamp or
> promo_type, and so are **not** caught by `selectors._is_digital_only`.
> Intro Pack foils, a Gift Box card and event promos round it out.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ktk` | expansion | 293 | 2014-09-26 | parent — booster set 1–269 (basics 250–269) + 24 Arena-only `Ny` prints |
| `pktk` | promo | 56 | 2014-09-26 | prerelease `Ns` datestamped (40) + Promo Pack `Np` stamped (6) + Intro Pack foils (5) + game day / release / buy-a-box / Gift Box (5) |
| `tktk` | token | 13 | 2014-09-26 | tokens |

`set:ktk+related` covers all three.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 269 | `ktk` 1–269 (121 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $140 nonfoil / $341 foil (Polluted Delta 239 ~$20, Bloodstained Mire 230 ~$19, Wooded Foothills 249 ~$18, Flooded Strand 233 ~$16, Windswept Heath 248 ~$12, Altar of the Brood 216 ~$10) |
| **Arena-only `y` prints** | 24 | `ktk` `16y`…`237y` (7 C / 8 U / 7 R / 2 M; nonfoil, unpriced, **own art**, released 2023-12-12) | `regular` | **⚠ digital — should never be listed, but is**: no `security_stamp`, no `promo_types`, so `_is_digital_only` misses them and `set:ktk` selectors include them (the 9 R/M would reach missing-set's rare/mythic lists) |

**`promo_types` dupe-foil / stamped signals:**

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `prerelease` + `datestamped` | `regular` | yes | 40 prints, auto-dropped (~$177 foil) |
| `promopack` + `stamped` | `regular` | **yes** | 6 prints, ~$24 / $44 |
| `intropack` | — | **no** — own art | 5 foil rares (Ankle Shanker 164, Avalanche Tusker 166, Ivorytusk Fortress 179, Rakshasa Vizier 193, Sage of the Inward Eye 195) |
| `gameday` / `release` / `buyabox` / `giftbox` | — | **no** — own art | Utter End 210, Heir of the Wilds 134, Dragon Throne of Tarkir 219, Rattleclaw Mystic 144, Sultai Charm 204 |

No fancy-foil sheet → configured `[dupe_foil] ktk = []` (2026-11-08) to enable `mm query missing-set ktk`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ktk = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| Arena-only `Ny` prints | 24 | **exclude — but fix in code, not config:** extend `_is_digital_only` to treat Scryfall `availability`/`digital` (or a `y`-suffix CN with no paper availability) as digital. Until then an interim rule could target CNs ending in `y` |
| `pktk` promo-pack stamped `Np` | 6 | **exclude** — `promo_types_any_of = ["stamped"]`; ~$24 |
| `pktk` Intro Pack foils + event promos | 10 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` / `Np` | `pktk` | prerelease / Promo Pack | — |
| `164`, `166`, `179`, `193`, `195` | `pktk` | Intro Pack foil (alt art) | Ankle Shanker 164 |
| `134`, `210` | `pktk` | Game Day | Utter End 210 |
| `219` / `144` / `204` | `pktk` | Release / Buy-a-Box / Gift Box | Rattleclaw Mystic 144 |

---

## 7. Edge cases & gotchas

- **`Ny` CNs are digital.** MTGJSON marks them `availability: ["arena"]`;
  Scryfall dates them 2023-12-12. The local `cards` table keeps no
  availability column, so only the CN suffix and date give them away.
- **Prerelease packs are per-clan** (`prerelease-<clan>`, EV ~$4.60–$8.16).
- Dragon Throne of Tarkir 219 carries `datestamped` but has its own art; `missing.drop_datestamped_with_sibling`
  drops it from missing-set (it matches name + treatment, not art).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] ktk = []` — configured 2026-11-08 (enables `mm query missing-set ktk`).
- `config/families.toml` `[[unobtainable.ktk.rules]]` — 2 proposed rules, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.ktk]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | each with a foil `pktk` rare |
| Event Deck *Conquering Hordes* | Event deck | — |
| Fat Pack / Holiday Gift Box | Bundle / gift bundle | land packs (pools); `pktk` 204 |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ktk --list-boosters` (2026-11-05): `draft` EV ~$4.29; `prerelease-<clan>` ~$4.60–$8.16; `arena` (digital code card, ignore).
