# `avr` — Avacyn Restored

> Per-family memory doc. Read this before answering set-specific questions about
> `avr` or working on `avr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `avr`
**Family root type:** `expansion`
**Family released:** 2012-05-04
**Last audit:** 2026-11-05 via `/characterize-set avr` (one-at-a-time run — tier decisions pending owner review).

---

> **Third Innistrad set — miracles, soulbond, Cavern of Souls, Griselbrand.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `avr` | expansion | 244 | 2012-05-04 | parent — booster set 1–244 (basics 230–244) |
| `pavr` | promo | 6 | 2012-05-04 | prerelease Moonsilver Spear `217★` + release Restoration Angel `32★` + buy-a-box Silverblade Paladin `36★` + Game Day Killing Wave 111 / Latch Seeker 63 + resale Angel of Glory's Rise `A9` |
| `phel` | memorabilia | 5 | 2012-05-04 | The Helvault promo box — Avacyn 6, Griselbrand 106, Bruna 208, Gisela 209, Sigarda 210 (same art as `avr`, ~$66 nonfoil) |
| `tavr` | token | 8 | 2012-05-04 | tokens |

`set:avr+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 244 | `avr` 1–244 (116 C / 60 U / 53 R / 15 M; 11 miracles) | `regular` | rarity/base sub-selectors — R+M ≈ $284 nonfoil / $832 foil (Cavern of Souls 226 ~$51 / $94, Avacyn, Angel of Hope 6 ~$45 / $91, Exquisite Blood 102 ~$41, Craterhoof Behemoth 172 ~$24, Griselbrand 106 ~$9 / $54) |

**`promo_types`:** every `pavr` print except the resale `A9` has its own art (Killing Wave 111 ~$10). No `datestamped` token on these, so missing-set keeps the prerelease and release promos. No fancy-foil sheet →
configured `[dupe_foil] avr = []` (2026-11-08) to enable `mm query missing-set avr`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] avr = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pavr` promos | 6 | **owner's call** — 5 of 6 have their own art |
| `phel` Helvault | 5 | already off by default (memorabilia); same art as `avr` |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pavr` | prerelease / release / Buy-a-Box (alt art) | Restoration Angel `32★` |
| `63`, `111` | `pavr` | Game Day | Killing Wave 111 |
| `A9` | `pavr` | resale (same art) | Angel of Glory's Rise |
| same CN as `avr` | `phel` | The Helvault (in-store) | Griselbrand 106 |

---

## 7. Edge cases & gotchas

- **`frame_effects` `miracle`** (11 prints) is the miracle frame — cosmetic.
- **`phel` is memorabilia** but holds real, playable cards (same art as `avr`); master-list skips it by default.
- MTGJSON lists a `six` booster type besides `draft`.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] avr = []` — configured 2026-11-08 (enables `mm query missing-set avr`).
- `config/families.toml` `[[unobtainable.avr.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.avr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 / Event Decks ×2 | Intro pack / Event deck | Death's Encroach, Humanity's Vengeance |
| The Helvault Promo Box | box set (MTGJSON `Box Set`) | `phel` |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py avr --list-boosters` (2026-11-05): `draft` EV ~$6.74.
