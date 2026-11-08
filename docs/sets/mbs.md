# `mbs` — Mirrodin Besieged

> Per-family memory doc. Read this before answering set-specific questions about
> `mbs` or working on `mbs`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mbs`
**Family root type:** `expansion`
**Family released:** 2011-02-04
**Last audit:** 2026-11-05 via `/characterize-set mbs` (one-at-a-time run — tier decisions pending owner review).

---

> **Second Scars of Mirrodin set — Mirran vs. Phyrexian faction boosters (Blightsteel Colossus, Sword of Feast and Famine).** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mbs` | expansion | 155 | 2011-02-04 | parent — booster set 1–155 (basics 146–155) |
| `pmbs` | promo | 4 | 2011-02-04 | prerelease Hero of Bladehold `8★` / Glissa `96★` + release Thopter Assembly `140★` + buy-a-box Mirran Crusader `14★` |
| `tmbs` | token | 6 | 2011-02-04 | tokens |

`set:mbs+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 155 | `mbs` 1–155 (70 C / 40 U / 35 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $236 nonfoil / $765 foil (Blightsteel Colossus 99 ~$45 / $139, Sword of Feast and Famine 138 ~$44, Consecrated Sphinx 21 ~$33, Green Sun's Zenith 81 ~$31, Inkmoth Nexus 145) |

**`promo_types`:** all four `pmbs` prints have their own art. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] mbs = []` (2026-11-08) to enable `mm query missing-set mbs`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] mbs = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pmbs` promos | 4 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `pmbs` | prerelease / release / Buy-a-Box (alt art) | Hero of Bladehold `8★` |

---

## 7. Edge cases & gotchas

- **Faction boosters:** MTGJSON lists `mirran` (EV ~$5.71) and `phyrexian` (~$9.94) booster types alongside `draft` (~$7.80) — the two prerelease/faction packs.
- MTGJSON has 4 Intro Packs, 2 Event Decks and Deck Builder's Toolkit lists.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] mbs = []` — configured 2026-11-08 (enables `mm query missing-set mbs`).
- `config/families.toml` `[[unobtainable.mbs.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.mbs]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Mirran / Phyrexian faction packs | prerelease pack | — |
| Intro Packs ×4 / Event Decks ×2 | Intro pack / Event deck | Infect & Defile, Into the Breach |
| Fat Pack | Bundle | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py mbs --list-boosters` (2026-11-05): `draft` EV ~$7.80; `mirran` ~$5.71; `phyrexian` ~$9.94.
