# `roe` — Rise of the Eldrazi

> Per-family memory doc. Read this before answering set-specific questions about
> `roe` or working on `roe`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `roe`
**Family root type:** `expansion`
**Family released:** 2010-04-23
**Last audit:** 2026-11-05 via `/characterize-set roe` (one-at-a-time run — tier decisions pending owner review).

---

> **Standalone large set — the Eldrazi titans, levelers, totem armor.** Base frame only. Its promo set follows the 2012–2014 pattern:
> **`N★` alt-art foils** (prerelease, release, buy-a-box) plus Game Day
> promos — no Promo Pack, no stamped dupes.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `roe` | expansion | 248 | 2010-04-23 | parent — booster set 1–248 (basics 229–248) |
| `proe` | promo | 3 | 2010-04-23 | prerelease Emrakul, the Aeons Torn `4★` (~$33) + release Lord of Shatterskull Pass `156★` + buy-a-box Guul Draz Assassin `112★` |
| `troe` | token | 7 | 2010-04-23 | tokens |

`set:roe+related` covers all.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 248 | `roe` 1–248 (120 C / 60 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $353 nonfoil / $1618 foil (Kozilek 6 ~$48 / $173, Ulamog 12 ~$35 / $148, Emrakul 4 ~$29 / $196, Lighthouse Chronologist 75 ~$26, Linvala 33 ~$24 / $107, Bear Umbra 177) |

**`promo_types`:** all three `proe` prints have their own art; the prerelease Emrakul `4★` (~$33) is the priciest. The prerelease and release promos carry `datestamped`, so `missing.drop_datestamped_with_sibling` drops them from missing-set (name + treatment match, not art). No fancy-foil sheet →
configured `[dupe_foil] roe = []` (2026-11-08) to enable `mm query missing-set roe`.

---

## 3–4.

No chase variants among uncommons; no scenes.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] roe = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `proe` promos | 3 | **owner's call** — all have their own art |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `proe` | prerelease / release / Buy-a-Box (alt art) | Emrakul `4★` |

---

## 7. Edge cases & gotchas

- **Very high foil premium** (R+M ~$353 nonfoil vs ~$1,618 foil).
- MTGJSON lists a `six` booster type besides `draft`, plus Deck Builder's Toolkit lists.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] roe = []` — configured 2026-11-08 (enables `mm query missing-set roe`).
- `config/families.toml` `[[unobtainable.roe.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.roe]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Intro Packs ×5 | Intro pack | — |
| Fat Pack / Deck Builder's Toolkit | Bundle / kit | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py roe --list-boosters` (2026-11-05): `draft` EV ~$9.21.
