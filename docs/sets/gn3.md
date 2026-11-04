# `gn3` — `Game Night: Free-for-All`

> Per-family memory doc. Read this before answering set-specific questions about
> `gn3` or working on `gn3`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gn3`
**Family root type:** `box` (standalone boxed product, `parent_set_code: null`)
**Family released:** 2022-10-14
**Last audit:** 2026-11-01 via `/characterize-set gn3` (non-interactive batch run).

---

> **Boxed multiplayer product, not a booster set.** `gn3` is the contents of ONE
> sealed SKU — *Magic Game Night: Free-for-All* — five fixed 60-card decks plus
> tokens. Everything is base-frame (`2015`) nonfoil except the five deck-leader
> mythics, which are **foil-only** and exist in no other set. No boosters, no
> showcase/borderless/etched tier. Track it as five precons (`Game Night Deck`),
> not via booster EV.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gn3` | box | 135 | 2022-10-14 | parent — CN 1–136 (**CN 66 does not exist**, see §7) |
| `tgn3` | token | 10 | 2022-10-14 | Game Night: Free-for-All Tokens, CN 1–10, foil+nonfoil, unpriced |

**Separately-rooted bonus sheets:** none. Scryfall `/sets` in the 2022-09-15 →
2022-11-15 window shows only `tgn3` linked to `gn3`; neighbours (`unf`/`ulst`,
`40k`, `slc`, `ydmu`, `prcq`) are unrelated families. Not a bonus sheet of any
other family. Earlier Game Night products (`gnt` 2018, `gn2` 2019) are separate
standalone roots, not linked to `gn3`.

No `--only` needed: `mm set master-list gn3` resolves to `gn3` (the anchor is
always included even though `box` is not in `sets.DEFAULT_INVENTORY_SET_TYPES`);
`tgn3` is skipped by default as a token set — pass `--include token` to
checklist the tokens.

---

## 2. Treatments

Survey (`survey_treatment_signature.py GN3`, 145 prints incl. tokens): every
print computes to `regular` — 140 nonfoil-available, 15 foil-available. No
`promo_types` at all, no showcase, borderless, extended-art, etched, or
fancy-foil tier. All `frame: 2015`, `border_color: black`, `security_stamp: oval`
on the mythics.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (nonfoil-only) | 130 | `gn3` 6–136 (no 66) | `regular` | handled by rarity/base sub-selectors |
| deck-leader mythics (**foil-only**) | 5 | `gn3` 1–5 | `regular` (foil) | handled by mythic sub-selector — unique cards, not a dupe-foil |
| tokens (foil+nonfoil) | 10 | `tgn3` 1–10 | `regular` | tokens — hard-excluded from missing-set (`is_token`) |

`frame_effects`: `legendary` on 8 prints (the 5 mythics + Danitha Capashen 9,
Vilis 63, Drakuseth 76); 137 none. Cosmetic only.

**Deck-leader mythics (foil-only, new to Magic in `gn3`, no other printing):**
Zamriel, Seraph of Steel (1, W, $8.46), Maeve, Insidious Singer (2, U, $12.41),
Vogar, Necropolis Tyrant (3, B, $13.70), Nogi, Draco-Zealot (4, R, $4.20),
Imaryll, Elfhame Elite (5, G, $17.76). These are the only `not:reprint` cards
in the set.

**Base CN bands (colour-sorted, all reprints):** W 6–21, U 22–42, B 43–65,
R 67–88, G 89–112, artifacts 113–121, basics 122–136 (3 arts each of
Plains/Island/Swamp/Mountain/Forest).

**`promo_types` dupe-foil / stamped signals:** none — no print carries any
`promo_types` token, and no print computes to `ff`. A `[dupe_foil]` list has
nothing to drop → proposed `gn3 = []`.

**Full-art convention:** `full_art = false` on every print.

---

## 3. Chase variants

Only the basic lands trip `chase` (threshold 3): `mm query show 'set:gn3+related chase'`
→ 15 rows, CN 122–136, commons ~$0.09–0.40. No nonland card has more than one
printing in the family.

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Plains / Island / Swamp / Mountain / Forest | 3 each | `gn3` 122–136 | common | regular |

---

## 4. Scenes / posters / panoramas

n/a — no borderless prints at all, so no scene/poster runs.

---

## 5. Unobtainable rules

None configured. No kept-by-default alt-treatment tier (showcase/borderless)
exists, so there is no keep/exclude decision on treatments.

**Scarcity check:** `set_status.py gn3` prints no ⚠ concentration note (family
not configured, so missing $ isn't computed). Whole set (135 prints) ≈ $165 at
2026-11-02 prices; the top is ordinary singles — Imaryll $17.76, Vogar $13.70,
Maeve $12.41, Vilis $9.63, Beast Whisperer $9.16, Elven Ambush $9.12, Zamriel
$8.46. No promo/scarcity tier to exclude.

**Missing-set baseline (2026-11-02):** 0 owned; `mm query missing-set gn3`
currently refuses (no `[dupe_foil]` entry). Proposed `gn3 = []` unblocks it and
filters nothing.

---

## 6. PRM destinations

n/a — no `pgn3` promo set and no promo prints. The five foil mythics live in
`gn3` itself at CN 1–5.

---

## 7. Edge cases & gotchas

- **CN 66 is missing.** Scryfall's `gn3` runs CN 1–136 but holds 135 cards —
  `/cards/gn3/66` 404s and MTGJSON's GN3 file also jumps 65 (Vow of Torment) →
  67 (Abrade). Not a sync gap; nothing to buy.
- **Foil-only mythics.** CN 1–5 have `finishes: ["foil"]` only (no nonfoil
  price). A checklist/ingest of these must use the foil column; a "nonfoil
  Zamriel" doesn't exist.
- **Token count mismatch.** The sealed product lists "15 Double Sided Tokens";
  Scryfall/MTGJSON catalog 10 token faces in `tgn3` (Angel, Human Soldier,
  Soldier, Bird Illusion, Drake, Demon, Zombie, Dragon, Elf Warrior, Treasure).
  The MTGJSON deck files carry no `tokens` board, so `import-precon` won't add
  tokens — add `tgn3` tokens ad hoc if wanted.
- No digital-only/arena-stamped prints leak (`mm query show 'set:gn3+related missing' | grep -i arena` → 0).
- No meld backs, serialized prints, or name collisions across siblings.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gn3.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gn3]]` — none (no scenes).

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Magic Game Night: Free-for-All (MTGJSON sealed `Magic Game Night Free For All Set`, `box_set`/`game_night`, cardCount 300) | Game Night deck box | Contains the 5 decks below + 5 spindowns, 5 spindown platforms, 15 double-sided tokens, 20 +1/+1 counters, rulebook, 5 reference cards. |
| Boundless Elves | Game Night Deck (`PRECON_MODERN_TYPES`) | `BoundlessElves_GN3`, 60 cards, mono-G, leader Imaryll (CN 5 foil) |
| Dark Sacrifice | Game Night Deck | `DarkSacrifice_GN3`, 60 cards, mono-B, leader Vogar (CN 3 foil) |
| Draconic Fury | Game Night Deck | `DraconicFury_GN3`, 60 cards, mono-R, leader Nogi (CN 4 foil) |
| Glorious Combat | Game Night Deck | `GloriousCombat_GN3`, 60 cards, mono-W, leader Zamriel (CN 1 foil) |
| Political Trickery | Game Night Deck | `PoliticalTrickery_GN3`, 60 cards, mono-U, leader Maeve (CN 2 foil) |

Each deck is mainBoard-only (no commander/sideboard board); the foil mythic is a
1x mainBoard entry. Add a whole box with `mm deck add-precon gn3 --all`.

**Booster types (for `sealed-value` EV):** none — `sealed_value.py gn3
--list-boosters` → "no booster data in MTGJSON". Value the box as its five decks.
