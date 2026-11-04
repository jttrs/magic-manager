# `mdd` — Marvel: Darkhold Destiny

> Per-family memory doc. Read this before answering set-specific questions about
> `mdd` or working on `mdd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mdd`
**Family root type:** `expansion` (Universes Beyond Marvel set, own null-parent root)
**Family released:** 2027-04-09 (**UNRELEASED** at audit time — preview season)
**Last audit:** 2026-11-01 via `/characterize-set mdd` (steps 1-8, non-interactive batch run).

> ⚠️ **Preview-season snapshot.** Scryfall lists only **19 printings** across the
> family (12 `mdd` + 1 `mdc` + 6 `tmdd`) — early spoilers, not the set. Every
> count below is a placeholder; **re-run `/characterize-set mdd` after release**
> (full spoiler + booster treatments, then re-sync `mm set sync mdd --include-related`).
> Nothing is owned yet.

---

## 1. Family map

| Code | `set_type` | Cards (Scryfall, 2026-11-01) | Released | Notes |
|---|---|---:|---|---|
| `mdd` | expansion | 12 | 2027-04-09 | parent (`parent_set_code: null`) |
| `mdc` | commander | 1 | 2027-04-09 | Darkhold Destiny Commander (`block_code: cmd`) — only Gargantos, the Endbringer (CN 399) spoiled |
| `tmdd` | token | 6 | 2027-04-09 | tokens (`is_token` → never in missing-set) |

`mm set list-related mdd` returns exactly these three; default `set:mdd+related`
resolution works, no `--only` needed. A `/sets` scan of 2027-03-01…2027-06-01
shows no other codes (no `pmdd` prerelease code, no art series, no bonus sheet
yet). Expect promo / art-series / front-card codes to appear closer to release.

**Not the same product as `msh` / `spm` / `mar`.** Fourth separate Marvel UB root:
`spm` (Marvel's Spider-Man, 2025-09, with `mar` bonus sheet — see
[`spm.md`](spm.md)), `msh` (Marvel Super Heroes, 2026-06 — see [`msh.md`](msh.md)),
and `mdd` (this, 2027-04). Don't conflate.

---

## 2. Treatments

Preview data only — **no alt-treatment tier has been spoiled yet.**

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 19 (13 non-token) | `mdd` 28–301, `mdc` 399 | `regular` | handled by rarity/base sub-selectors |
| showcase | 0 | — | `shw` | none spoiled yet — will need a keep/exclude decision when it appears |
| borderless | 0 | — | `b` | none spoiled yet |
| extended-art | 0 | — | `ext` | none spoiled yet (would be auto-dropped) |
| etched / fancy foil | 0 | — | `ff` | none spoiled yet |

- `frame_effects`: 14 none, 4 `legendary` (The Darkhold 92, Hela 106, Magik 242,
  Gargantos `mdc` 399), 1 `enchantment` (tmdd 8 Spirit Sorcerer token).
- `finishes`: all 19 `nonfoil+foil`. `border_color`: all `black`. `full_art`: all false.
- `security_stamp: oval` on rares/mythics (92, 106, 107, 242, `mdc` 399).

**`promo_types` signals:** only `universesbeyond` (6/19 — the tmdd tokens; the
spoiled `mdd`/`mdc` cards don't carry it yet in preview data). No fancy-foil token
→ no dupe-foil candidate yet.

**Full-art convention:** false everywhere (preview data).

---

## 3. Chase variants

None — `set:mdd+related chase` returns 0 rows (no card has ≥3 distinct-art
printings in preview data). Re-check after release.

---

## 4. Scenes / posters / panoramas

n/a — no borderless prints spoiled yet.

---

## 5. Unobtainable rules

None. No alt-treatment tier exists in the data yet, so there is nothing to keep
or exclude (`set_status.py mdd`: missing not available until `[dupe_foil]` is
configured; no ⚠ concentration note). Revisit after release.

---

## 6. PRM destinations

n/a — no promo code (`pmdd` etc.) exists on Scryfall yet; `bulk-add` has no
`mdd` mentions.

---

## 7. Edge cases & gotchas

- **Unreleased:** no prices (`prices_usd` null for every printing), no MTGJSON
  decks (`mm mtgjson decks --set mdd|mdc` → none), no booster data.
- DFCs: Hela, Mistress of Darkness // Dark Tutor (106) and Magik, Illyana
  Rasputin // Darkchild, Demon Uncaged (242).
- Basic lands spoiled at sparse CNs (Plains 292, Island 294, Swamp 296,
  Mountain 298, Forest 301) — the even-step gaps suggest 2 arts per basic, but
  Forest at 301 breaks the pattern; confirm the land cycle's CNs after release.
- `mdc` is filed with `set_type: commander` + `block_code: cmd` (normal), CN 399
  suggests the commander decks' new cards start high.
- Arena check: `set:mdd+related missing` shows no arena-stamped rows.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.mdd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.mdd]]` — None configured yet.

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Darkhold Destiny Commander decks (`mdc`) | Commander deck | Not yet in MTGJSON DeckList (no `fileName`s); deck names unknown |

**Booster types (for `sealed-value` EV).** `scripts/sealed_value.py mdd --list-boosters`
→ "no booster data in MTGJSON" (unreleased). Re-run after release.
