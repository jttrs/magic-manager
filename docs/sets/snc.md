# `snc` — Streets of New Capenna

> Per-family memory doc. Read this before answering set-specific questions about
> `snc` or working on `snc`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `snc`
**Family root type:** `expansion`
**Family released:** 2022-04-29 (NCC same day; promos through 2022-09)
**Last audit:** 2026-08-24 via `/characterize-set snc` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards | Notes |
|---|---|---:|---|
| `snc` | expansion | 513 | parent |
| `ncc` | commander | 447 | New Capenna Commander (5 decks: Bedecked Brokers, Cabaretti Cacophony, Maestros Massacre, Obscura Operation, Riveteers Rampage) |
| `psnc` | promo | 161 | Streets of New Capenna Promos (prerelease `Ns` + promopack `Np` stamps) |
| `pncc` | promo | 75 | New Capenna Commander Promos (promopack-stamped commander cards) |
| `asnc` | memorabilia | 81 | Art Series (not in default checklist) |
| `msnc` | minigame | 3 | Minigame cards (not in default checklist) |
| `ysnc` | alchemy | 30 | Alchemy digital-only (globally filtered) |
| `tsnc` | token | 19 | tokens (not in default checklist) |
| `tncc` | token | 36 | commander tokens |
| `ptsnc` | promo | 6 | SE-Asia token promos |

Default `set:snc+related` resolution works. `snc`/`ncc`/`psnc`/`pncc` are the
collectable bundle (expansion/commander/promo). No separately-rooted bonus sheet
gotcha.

---

## 2. Treatments

**`gilded` is SNC's fancy-foil dupe signal** — the golden art-deco showcase foil.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `gilded` | `ff` (+`b`/`shw`) | **yes** → `FAMILY_DUPE_FOIL_PROMO_TYPES` | 45 prints, CN 361-405, foil-only, `gilded+boosterfun` on a showcase+inverted frame. Every one has an exact same-name `boosterfun` showcase+inverted sibling (CN 296-340) — **same art, just the gilded golden foil**. Verified on Brazen Upstart (361 gilded ↔ 296 boosterfun, same frame_effects). |
| `boosterfun` | `b`/`shw`/`ext` | n/a (base fancy) | the non-gilded showcase (296-340) is the preferred representative kept by missing-set. |
| `promopack` + `stamped` | (stamp) | n/a — see §5 | 160 prints across psnc/pncc/snc; the scarcity tier the user rules out (§5). |
| `prerelease` + `datestamped` | (stamp) | yes → global preferred filter | 80 psnc `Ns` prints. |
| `alchemy` + `rebalanced` | (digital) | n/a | 44 ysnc/snc A-prefixed digital-only, globally filtered. |
| `concept`/`setextension`/`stepandcompleat` | (phyrexian-invasion crossover) | n/a | 2 SNC 469-ish Urabrask concept-Praetor prints; kept (unique art). |

**Full-art convention:** standard-era (2022) — borderless-inverted showcase cards
do NOT set `full_art: true` (predates the SPM/TLA convention flip).

---

## 3. Chase variants

`mm query show 'set:snc+related chase'` surfaces mostly the psnc `Np`/`Ns`
promo-pack + prerelease stamp pairs (Depopulate 10p/10s, Elspeth Resplendent
11p/11s, …) — these are the §5 stamped tier, not true multi-art chases.

**Gala Greeters (SNC 450-458)** — a genuine 9-artist variant uncommon (each a
distinct art by a different artist). Surfaces via the uncommon-chase sub-selector.
Not a scene (no spatial panorama); a collectable multi-art set.

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted range (SNC 285-295) is individual showcase
cards by mixed artists (Dominik Mayer / Anato Finnstark), not a contiguous
single-artist panorama. No `FAMILY_SCENES["snc"]` entry needed.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["snc"]` = one rule excluding `promopack`/`stamped`
(added 2026-08-24).

**Rationale.** Without it, missing-set totals **$2,069.10 / 281 prints**; the
top of the list is entirely `pncc`/`psnc` promo-pack-**stamped** cards (Currency
Converter `pncc` 81p $182, Smuggler's Share `pncc` 21p $100, …). These are
scarcity-priced stamp variants the user doesn't shop for. They normally fall to
the global preferred filter (`promopack`/`stamped` are in
`sets.EXCLUDED_PROMO_TYPES`), but the commander-promo (`pncc`) and prerelease
(`psnc`) prints have **no non-stamped sibling in the family graph** for the
datestamped-with-sibling filter to substitute, so they survive. This rule drops
them explicitly.

| Signal | What it catches | ~Value removed |
|---|---|---|
| `promopack` OR `stamped` | 160 prints across `pncc` (75), `psnc` (80), `snc` (5) — promo-pack + prerelease stamp variants | ~$1,697 |
| `stepandcompleat` | `snc` 469 Urabrask — the Phyrexian "Step-and-Compleat" premium foil of the same borderless concept art as `snc` 468 (which is kept). Foil-only. NOT caught by the dupe-foil filter because it computes to treatment `b`, not `ff` — so it lives here, not in FAMILY_DUPE_FOIL_PROMO_TYPES. | ~$16 |

Effect: missing-set drops to the realistic **~$371.66 / 121 prints** (topped by
the boosterfun showcase dual lands — Jetmir's Garden `snc` 291 ~$23, etc.).

Globally filtered (not via this rule): `alchemy`/`rebalanced` (digital),
`serialized` (none in SNC).

---

## 6. PRM destinations

| Physical stamp | Scryfall set | Channel |
|---|---|---|
| Prerelease datestamped, CN `Ns` (e.g. `34s`) | `psnc` | Set prerelease |
| Promo-pack stamped, CN `Np` (e.g. `34p`) | `psnc` | Promo pack |
| Commander promo, stamped | `pncc` | NCC promo |

Resolve a PRM-stamped SNC card by name + the `s`/`p` CN suffix per
`.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`gilded` is foil-only** (`finishes: ["foil"]`) — the golden showcase has no
  nonfoil version; its dupe representative (boosterfun showcase 296-340) has both.
- **Two `Tenuous Truce` printings in `ncc`** (87, 95) — a name collision; distinct
  scryfall_ids. Match by CN, not name.
- **Urabrask, Heretic Praetor — two borderless concept prints:** `snc` 468
  (`concept+boosterfun+setextension`, nonfoil+foil, ~$7/$9, KEPT — legit gap) and
  `snc` 469 (same art + `stepandcompleat` Phyrexian foil, foil-only, ~$16,
  EXCLUDED via §5 unobtainable rule). Same illustration; 469 is just the premium
  foil process. See §5.
- **`ncc` is a genuine `set_type: commander`** (5 real precons), unlike TMT's
  `tmc`/Avatar's `tle` (eternal-typed). No topology gotcha.
- **Alchemy A-prefixed** prints (snc A-###) — digital-only, globally filtered via `rebalanced`/`alchemy` promo_types.
- **`ysnc` Alchemy-ORIGINAL cards** — carry NO rebalanced/alchemy promo_type, only `security_stamp: "arena"`. Characterizing SNC surfaced that these leaked into missing-set (20 rows) because `_is_digital_only` only checked promo_types and the selector projection dropped `security_stamp`. Fixed 2026-08-24: `_is_digital_only` now treats `security_stamp == "arena"` as digital-only, and `_CARD_COLS`/`_card_dict` carry the stamp. This was a cross-family bug (any family with an Alchemy-original sibling); FIN's `yfin` happened to carry the promo_type so it never leaked.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["snc"]` = `frozenset({"gilded"})`
  — **configured 2026-08-24.** Drops the 45 gilded golden-foil dupes (361-405),
  keeps the boosterfun showcase (296-340) as the preferred representative. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["snc"]` = two rules —
  `{"promo_types_any_of": {"promopack", "stamped"}}` (160 stamp variants, ~$1,697)
  and `{"promo_types_any_of": {"stepandcompleat"}}` (snc 469 Step-and-Compleat
  foil, ~$16). **configured 2026-08-24.** §5.
- No `FAMILY_SCENES["snc"]` (no panoramas — §4).
