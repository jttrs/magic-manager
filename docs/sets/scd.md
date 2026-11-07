# `scd` — `Starter Commander Decks`

> Per-family memory doc. Read this before answering set-specific questions about
> `scd` or working on `scd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `scd`
**Family root type:** `commander` (standalone precon product — 5 two-colour "Starter Commander" decks)
**Family released:** 2022-12-02
**Last audit:** 2026-11-02 via `/characterize-set scd` (batch run; tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `scd` | commander | 352 | 2022-12-02 | parent — `parent_set_code: null`; all-reprint contents of the 5 decks |
| `tscd` | token | 27 | 2022-12-02 | tokens + 2 emblems (Ob Nixilis Reignited, Sarkhan the Dragonspeaker); 25 tokens foil+nonfoil |

No separately-rooted bonus sheet (Scryfall `/sets` 2022-11-15 → 2022-12-31 checked 2026-11-02: neighbours are `j22`/`fj22`, `30a`, `ea2`, `bro` family — none belong here). No oversized `oscd` set exists. `set:scd+related` = `scd` + `tscd`; no `--only` needed.

**The 5 decks** (MTGJSON `type: Commander Deck`, each led by a **foil-etched** commander at CN 1–5):

| Deck (MTGJSON `fileName`) | Commander (CN) | Colours |
|---|---|---|
| `DraconicDestruction_SCD` | Atarka, World Render (1) | RG |
| `TokenTriumph_SCD` | Emmara, Soul of the Accord (2) | GW |
| `GraveDanger_SCD` | Gisa and Geralf (3) | UB |
| `FirstFlight_SCD` | Isperia, Supreme Judge (4) | WU |
| `ChaosIncarnate_SCD` | Kardur, Doomscourge (5) | BR |

**CN layout:** 1–5 etched commanders; then by colour — W 6–41, U 42–65, B 66–121, R 122–170, G 171–215, multicolour 216–256, colourless/lands 257–352 (basics 333–352: 4 arts each of Plains/Island/Swamp/Mountain/Forest).

---

## 2. Treatments

Almost entirely regular-frame black-bordered reprints. `promo_types` is empty on every print (survey's promo_types section is blank).

**Frame/finish treatment classes present** (survey 2026-11-02, 379 prints incl. `tscd`):

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (nonfoil) | 347 | `scd` 6–352 | `regular` | handled by rarity/base sub-selectors |
| base (`legendary` frame effect) | 14 (within the 347) | scattered | `regular` | same class — legendary crown only |
| etched face commanders (`etched+inverted+legendary`, black border) | 5 | `scd` 1–5 | `b\|ff` | auto-dropped by `ff` collapse — see gotcha below |
| tokens (foil+nonfoil) | 27 | `tscd` 1–27 | `regular` | tokens hard-excluded from missing-set |
| showcase / borderless / extended-art | 0 | — | — | none present |

No KEPT-by-default alt tier (showcase/borderless) exists, so there is no keep/exclude decision to make.

**`promo_types` dupe-foil / stamped signals:** none. Proposed `[dupe_foil] scd = []` (unblocks `treatment=preferred`; filters nothing).

**Full-art convention:** `full_art = FALSE` everywhere (basics are regular-frame).

**⚠ Etched-commander gotcha:** CN 1–5 are the **only** `scd` printings of the five commanders (no nonfoil twin in-family), yet they compute to `b|ff` (the inverted frame effect reads as `b`). They are therefore NOT surfaced by `rarity=mythic treatment=regular` and `treatment=collectible-alt` returns 0 rows for the family — so a `missing-set scd` run would silently omit an un-owned face commander. Not an issue today (all 5 owned, 1 foil each).

---

## 3. Chase variants

None in the `_modifier_chase` (uncommon-regular) sense. Bare `set:scd+related chase` returns **20 rows = the basic lands** (4 arts × 5 basics, CN 333–352) — not a meaningful chase.

---

## 4. Scenes / posters / panoramas

None. No borderless / inverted-scene / poster prints.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review). None needed: no scarcity, stamped, serialized or alt-frame tier exists; top print is True Conviction (CN 38) at $5.47, nothing near $100.

**Missing-set baseline (2026-11-02):** owner holds all 352 `scd` printings (500 copies; 10 deck rows — 5 built + 5 deconstructed). `set:scd+related missing` = only the 27 `tscd` tokens (unpriced; tokens never enter missing-set buy lists). `set_status.py scd` reports Owned as 347 printings / 495 cards · $205.54 (the 5 etched commanders, 1 copy each, are not counted there — same `b|ff` blind spot as §2), Missing as "cross-set; n/a" (commander root), and emits **no** concentration warning.

---

## 6. PRM destinations

n/a — the product has no promo sibling (`pscd` does not exist); the etched commanders are deck-exclusive and live in `scd` itself.

---

## 7. Edge cases & gotchas

- **All reprints, cross-set names:** every card is a reprint whose name exists in other sets (e.g. Gisa and Geralf also `emn` 183); resolve a physical card by the `SCD` set stamp + CN, never by name.
- **Etched commanders:** see §2 gotcha — `b|ff`, invisible to the regular/collectible-alt sub-selectors.
- **Two Thopter tokens** (`tscd` 11 and 24) — distinct art, same name.
- **Emblems** live in `tscd` (26, 27) alongside tokens; `is_token` covers them.
- Digital-only check: `set:scd+related missing | grep -i arena` → no rows.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.scd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.scd]]` — None configured yet (none exist).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Starter Commander Deck ×5 (see §1 table for `fileName`s) | Commander deck | Sold individually and as a 5-deck bundle; each deck = etched commander (CN 1–5) + 99 reprints + its `tscd` tokens. Import with `mm deck add-precon` / `import-precon <fileName>`. |

**Booster types:** none — `sealed_value.py scd --list-boosters` → "no booster data in MTGJSON" (precon-only product; value the decks as decks).
