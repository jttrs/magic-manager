# `fdn` — Foundations

> Per-family memory doc. Read this before answering set-specific questions about
> `fdn` or working on `fdn`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `fdn`
**Family root type:** `core`
**Family released:** 2024-11-15 (Magic: The Gathering Foundations — the evergreen core set + a Jumpstart companion + Beginner Box / Starter Collection products)
**Last audit:** 2026-08-30 via `/characterize-set fdn` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `fdn` | core | 771 | parent — but only **171 truly-base** cards; the rest are product-tagged (see §7) |
| `j25` | draft_innovation | 779 | **Foundations Jumpstart** — a big companion pool (parents to `fdn`) |
| `pfdn` | promo | 106 | promos — 25 `promopack`+`stamped` (`Np`) + 80 `prerelease`+`datestamped` (`Ns`) + 1 buyabox Sol Ring |
| `afdn` | memorabilia | 55 | Art Series (not in default checklist) |
| `fj25` | memorabilia | 46 | Jumpstart Front Cards (roots to `j25`, a 2-level chain) |
| `ffdn` | memorabilia | 10 | Front Cards |
| `tfdn` | token | 33 | tokens |
| `fdc` | commander | 3 | Foundations Commander (tiny — 3 cards) |

Default `set:fdn+related` resolution works. **Topology is clean:** `fdn` is the
true parent (`parent_set_code: NULL`); every other code roots to it, including
the 2-level `fj25 → j25 → fdn`. The config key is **`fdn`** (the missing-set
filter resolves any member up to this parent). A member-code invocation
(`set-status j25`, `set-status fdc`) normalizes to `fdn` and reports the whole
family.

**Sync gotcha:** a bare `master-list fdn` may not pull every sibling; use
`mm set sync fdn --include-related` for the full family (esp. `pfdn`, whose 25
`promopack`+`stamped` scarcity tier is invisible until synced — the SNC/ECL/SOS/
BLB trap).

---

## 2. Treatments

**TWO same-art fancy-foil dupe signals**, both computing to `ff` (so Step-3
DUPE_FOIL catches both):

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `manafoil` | `b\|ff` / `fa\|ff` | **yes** → `FAMILY_DUPE_FOIL_PROMO_TYPES` | 60 prints (+`boosterfun`), the "mana foil" premium sheet over the boosterfun art. Verified: Abyssal Harvester 381 (`manafoil`, `b\|ff`) shares `illustration_id f13f17e1` with 316 (`boosterfun`, `b`). Dupe — keeps the boosterfun print. |
| `fracturefoil` | `shw\|ff` | **yes** → `FAMILY_DUPE_FOIL_PROMO_TYPES` | 10 prints (+`japanshowcase`+`boosterfun`), the EOE/ECL-style fracture-foil over the japanshowcase showcase art. Verified: Bloodthirsty Conqueror 436 (`shw\|ff`) shares `illustration_id d9a581b0` with japanshowcase 426 (`shw`). Dupe — keeps the japanshowcase print. |
| `japanshowcase` | `shw` | **no — distinct showcase art** | 20 prints (`boosterfun`+`japanshowcase`, CN 422-431 range). The showcase mythics (Doubling Season 428 foil ~$262, Llanowar Elves 429 ~$228) — kept as the preferred representative; their fracturefoil twins are the dupe. |
| `boosterfun` | `b` (+`shw`/`extendedart`) | **no — distinct alt-art** | 196 prints. Standard showcase/borderless/extended-art alt-arts, KEPT. |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 25 `pfdn` `Np` prints. Same card as a kept base sibling + a promo-pack stamp. Compute to `regular` → excluded via §5 `{stamped}` rule. |
| `prerelease` + `datestamped` | (stamp) | n/a — scarcity | 80 `pfdn` `Ns` prints. Auto-dropped by the generic Step-2 datestamped filter (each has a non-datestamped base sibling); no family rule needed. |
| `startercollection` / `beginnerbox` / `setextension` | (empty) | **no — structural, KEPT** | Product-distribution tags on the card's ONLY printing, NOT fancy foils (compute to empty/`regular`). See §7. |
| `doublerainbow` | — | n/a | 1 print: `pfdn` 1 Sol Ring (`buyabox`), distinct promo art, KEPT. |

**Full-art convention:** boosterfun showcase/borderless (2024 core set). No scenes.

---

## 3. Chase variants

No uncommon multi-variant chase surfaced. The premium tier is the japanshowcase
showcase mythics (CN 422-431: Doubling Season, Llanowar Elves, Bloodthirsty
Conqueror, Twinflame Tyrant, Progenitus, …) — distinct art, KEPT; their
`manafoil`/`fracturefoil` foils are the dupes (§2). **No serialized/headliner
ultra-rare exists in this family** — unlike the 2025 UB sets, so §5 has only the
`{stamped}` rule.

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted range (`fdn` 292+) is individual boosterfun
showcase cards by mixed artists (one per card) — not a contiguous single-artist
panorama. No `FAMILY_SCENES["fdn"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["fdn"]` = a single `{stamped}` rule (added 2026-08-30).

**`{stamped}`** — all 25 `pfdn` `promopack`+`stamped` (`Np`) promo-pack scarcity
variants (same card as a kept base sibling + a stamp). Validated: all 25
promopack cards ALSO carry `stamped`, and Foundations has **NO `promopack`-only
alt-art trap** (zero promopack-without-stamped prints in the family — unlike
SNC/EOE/ECL/BLB), so `{stamped}` is exact and safe.

**No serialized/headliner rule** — 0 such prints in the family. The lone
`doublerainbow` (`pfdn` 1 Sol Ring, a buyabox promo) is distinct art and KEPT.

**Missing-set impact:** with the config, the `preferred` slice drops from **162 →
92 prints** (the 60 manafoil + 10 fracturefoil dupes via DUPE_FOIL + the stamped
promos via this rule). Full `missing-set fdn` ≈ **410 prints / $2,003** at current
ownership — top prints are legit japanshowcase foil mythics (Doubling Season
~$262, Llanowar Elves ~$228), NOT a scarcity artifact. The `datestamped` `Ns`
promos auto-drop via the generic Step-2 filter (not this rule).

Globally filtered (not via a rule): `alchemy`/`rebalanced` (digital); the
`prerelease`+`datestamped` `Ns` promos (Step-2).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel |
|---|---|---|
| `Np` (e.g. `20p`) | `pfdn` | Promo pack — 25 `promopack`+`stamped` (excluded via §5) |
| `Ns` (e.g. `54s`, `134s`) | `pfdn` | Prerelease datestamped — 80 `prerelease`+`datestamped` (auto-dropped, §2) |
| Buy-a-Box Sol Ring | `pfdn` 1 | `doublerainbow`+`buyabox`, distinct promo, KEPT |

Resolve a PRM-stamped FDN card by name + the `p`/`s` CN suffix per
`.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **Only 171 of 771 `fdn` cards are truly-base** (empty `promo_types`). The rest
  carry a product tag: `startercollection` (278), `beginnerbox` (129),
  `setextension` (41, CN 731-771), plus the boosterfun/foil variants. These
  product tags are on the card's ONLY printing (e.g. Cat Collector CN 4 has no
  plain-frame twin — it IS the base card, just distributed via the Starter
  Collection). They compute to empty/`regular` treatment and flow through the
  normal rare/mythic sub-selectors — KEPT, not filtered. Do NOT mistake these for
  scarcity variants.
- **The Beginner Box decklist EXISTS and is retrievable** — via `sealedProduct` →
  its 10 component deck files (Cats_FDN … Wizards_FDN), which are typed `Jumpstart`
  in the DeckList. Do NOT conclude "no decklist" from a DeckList `type` scan; see §9
  and the [[mtgjson-search]] skill's sealedProduct warning. The `beginnerbox` /
  `startercollection` promo_type tags (§7 first bullet) are a separate card-level
  signal, not the product's decklist.
- **`j25` (Foundations Jumpstart) is a 779-card companion pool** rooted to `fdn`,
  so `set:fdn+related` includes it. It contributes a large share of the missing
  count (many distinct rares/mythics). Expected — it's a real product family
  members open.
- **`fj25 → j25 → fdn` is a 2-level parent chain** — `fj25` (Jumpstart Front
  Cards) roots to `j25`, which roots to `fdn`. `sets.resolve` walks the full
  chain, so all land in the same family.
- **`manafoil` is Foundations' unique dupe-foil name** — same mechanism as
  EOE/ECL `fracturefoil` (which ALSO appears here). Both compute to `ff`, so
  DUPE_FOIL (not UNOBTAINABLE_RULES) is correct.
- **No `promopack`-only alt-art trap** — unlike SNC/EOE/ECL/BLB, every `promopack`
  print here also has `stamped`, so the `{stamped}` rule has no distinct-art
  collateral.
- **`fdc` (Commander) is only 3 cards** — a token commander product, not a full
  precon deck set. `Precons | 3 jumpstart` in set-status reflects imported j25
  Jumpstart packs, not fdc.
- **"Phyrexian Arena" is not a digital card** — the name matches an `arena`
  grep but it's a normal card (`fdn` 322/386); no `security_stamp='arena'`
  digital-only leak in the family.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["fdn"]` = `frozenset({"manafoil", "fracturefoil"})`
  — **configured 2026-08-30.** Drops the 60 manafoil + 10 fracturefoil same-art
  dupes (both compute to `ff`); keeps the boosterfun + japanshowcase prints. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["fdn"]` = one rule —
  `{"promo_types_any_of": {"stamped"}}` (25 `pfdn` promo-pack stamps; all also
  carry `stamped`, no alt-art collateral). §5. **No `{headliner, serialized}`
  rule** — no such tier in this family.
- No `FAMILY_SCENES["fdn"]` (no panoramas — §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Foundations Jumpstart | Jumpstart | `j25` (779 cards) + `fj25` front cards. Imported via `mm set jumpstart-list j25` → ingest. |
| Beginner Box | Beginner Box | **Decklist IS retrievable** via `sealedProduct` "Foundations Beginner Box" (`box_set`/`starter_deck`, cardCount 200) → 10 component decks (Cats/Elves/Goblins/Healing/Inferno/Pirates/Primal/Undead/Vampires/Wizards), each a real MTGJSON deck file **typed `Jumpstart` in the DeckList** (so a `type` scan misses them — use `mtgjson.sealed_product_decks("fdn", "Foundations Beginner Box")`). Separately, the `beginnerbox` Scryfall promo_type tags 129 `fdn` cards — a card-level distribution signal, NOT the product decklist. No separate Scryfall set code. |
| Starter Collection | (card pool) | `sealedProduct` "Foundations Starter Collection" → ONE `StarterCollection_FDN` deck (387 cards, 278 distinct) — a build-your-own LIBRARY, not a playable deck, so it ingests as **pool** (auto-classified by name + card_count>150: cards loose in inventory, marker deck row). Also 3 random Play Boosters (not importable). Card-level `startercollection` tag on 278 `fdn` cards. No separate Scryfall set code. `mm deck add-precon fdn "Starter Collection"` auto-routes to pool. |
| Set extension | (structural) | `setextension` tag (41 `fdn` cards, CN 731-771) — the "extended" main-set slots. |
| Foundations Art Series | Art Series | `afdn` (55 cards, memorabilia). Not in default checklist. |
| Promo Pack | promo (`promopack`+`stamped`) | `pfdn` `Np` — 25-card scarcity tier excluded via §5. |
