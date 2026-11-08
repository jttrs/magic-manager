# `mar` — Marvel Universe (cross-set Marvel masterpiece sheet)

> Per-family memory doc. Read this before answering set-specific questions about
> `mar` or working on `mar`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `mar`
**Family root type:** `masterpiece` (`parent_set_code: null` — its own root)
**Family released:** 2025-09-26 → ongoing (waves ship inside each Marvel expansion's boosters)
**Last audit:** 2026-11-01 via `/characterize-set mar` (non-interactive batch run — tier decisions pending owner review).

---

> **⚠️ `mar` is NOT a Spider-Man bonus sheet.** It is a cross-set "Source Material"
> masterpiece sheet that feeds the boosters of MULTIPLE Marvel expansions — SPM
> (CN 1-40) and MSH (CN 41-100) so far, with more Marvel sets to come. Like
> SLD/SPG it is modeled as its own anchor and listed in
> `family_status.NON_FAMILY_SETS` (owned-$ only; `set_status.py mar` prints
> Missing/Characterized as "cross-set; n/a" even with this doc present). The
> SPM-side history (it was once mis-registered under `spm`'s `set_targets`) is in
> [`spm.md`](spm.md) §1; the MSH booster side is in [`msh.md`](msh.md).

---

## 1. Family map

`mm set list-related mar` (verified 2026-11-01):

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mar` | masterpiece | 100 | 2025-09-26 (CN 1-40) / 2026-06-26 (CN 41-100) | parent. Every card mythic, borderless-inverted, `sourcematerial`+`universesbeyond`, foil+nonfoil, `full_art: true`. CN 1-40 also carry `boosterfun` (SPM wave); CN 41-100 don't (MSH wave). |
| `lmar` | promo | 8 | 2025-09-30 → 2026-11-01 | Marvel Legends Series Inserts (Hasbro figure boxes), `parent_set_code: mar`. Foil-only, borderless-inverted, NOT `sourcematerial`. Grew from 4 → 8 cards (CN 5-8 released 2026-10-08 … 2026-11-01, unpriced at audit). |
| `omb` | masterpiece | 40 | 2025-09-23 | **Through the Omenpaths Bonus Sheet — DIGITAL-ONLY** (Scryfall set `digital: true`, `games: [arena, mtgo]`, no USD price). `parent_set_code: mar`. Black-bordered, nonfoil, no promo_types, no security stamp — the Omenpaths (non-Marvel) art of MAR 1-40, same names CN-for-CN. See §7 — it currently LEAKS into missing output. |

Wave split (informational — MAR is counted as one entity, not partitioned per expansion):

| CN band | Shipped in | MTGJSON sheet |
|---|---|---|
| `mar` 1-40 | SPM play + collector boosters | SPM `play.sourceMaterial` (40, nonfoil), `collector.nonFoilSourceMaterial` / `foilSourceMaterial` (40 each) |
| `mar` 41-100 | MSH play + collector boosters | MSH `play.sourceMaterial` (60, nonfoil), `collector.nonFoilSourceMaterial` / `foilSourceMaterial` (60 each) |

No separately-rooted bonus sheets beyond the two Scryfall children. No `--only` needed for the paper sheet itself; to keep the digital `omb` out of a checklist use:

```
mm set master-list mar --only mar,lmar
```

---

## 2. Treatments

Survey: `uv run python scripts/survey_treatment_signature.py MAR` (148 prints).

**Frame/finish treatment classes present:**

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| borderless source-material reskin (inverted) | 100 printings (×2 finishes) | `mar` 1-100 | `b\|sm` | **borderless — KEPT (default) — pending owner review.** This IS the sheet; there is no non-borderless MAR print. `mar` frame_effects: `inverted` 68, `enchantment+inverted` 20, `legendary+inverted` 11, `enchantment+legendary+inverted` 1. |
| borderless promo insert (inverted; 7 also `legendary`) | 8 (foil only) | `lmar` 1-8 | `b` | **borderless — KEPT (default) — pending owner review.** Distinct art from every other printing of each card (verified by `illustration_id`). |
| regular (black border, digital) | 40 (nonfoil) | `omb` 1-40 | `regular` | NOT filtered — digital-only but undetected (§7). |

No showcase, extended-art, etched, or fancy-foil (`ff`) classes exist in this family. Foil is plain traditional foil.

**`promo_types` signals:**

| promo_type | Count | Treatment keyword | Dupe of a sibling? | Notes |
|---|---:|---|---|---|
| `sourcematerial` | 100 | `sm` | no — each MAR print has unique art (0 `illustration_id` matches vs any non-MAR printing, incl. `omb`) | the masterpiece-sheet discriminator; drives `is_reskin` |
| `universesbeyond` | 108 | — | n/a | umbrella tag on `mar` + `lmar` |
| `boosterfun` | 41 | — | n/a | `mar` 1-40 + `lmar` 1 only (the SPM wave); MSH wave omitted it |

**No dupe-foil signal** → configured `[dupe_foil] mar = []` (2026-11-08).

**Full-art convention:** `full_art: true` on all 100 `mar` prints (supersedes the older note in `docs/scryfall-set-families-and-bonus-sheets.md` that MAR was mixed); `false` on `lmar` and `omb`. Security stamp: `oval` on all except `mar` 39 Alibou (`circle`); `lmar` `oval`; `omb` none.

**Reskins (`flavor_name`):** 15 of 108 paper prints carry a flavor name, e.g. `mar` 10 Lorthos → *Doc Ock, Armed and Dangerous*, 22 Skithiryx → *Venom, King in Black*, 51 Teferi's Protection → *T'Challa's Protection*, 99 Roaming Throne → *Doom Variant*, 100 Sword of Fire and Ice → *Patriotic Shield*, `lmar` 3 Huntmaster → *Colonel John Jameson*. The rest keep the oracle name (e.g. Wedding Ring).

---

## 3. Chase variants

`set:mar+related missing rarity=uncommon treatment=regular chase` → 0 rows (every MAR card is mythic). `set:mar+related chase` (all rarities):

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Heroic Intervention | 4 | `mar` 34 (Kirby & Ditko), 78 (Bob Layton), 79 (Kirby & Don Heck), 80 (Kirby & Dick Ayers) | mythic | `b\|sm` |

Below threshold (2 distinct arts, not flagged by `chase`): Path to Exile 4 / 47, Counterspell 9 / 52, Beast Within 33 / 75 (75 = *Grimm Fate*). Each of the duplicate names has one copy per wave.

---

## 4. Scenes / posters / panoramas

None. Artist-run scan over all 100 `mar` prints found no contiguous same-artist run ≥3 — art is classic Marvel comic cover/panel art by many artists (Jack Kirby ×8+co-credits, John Romita Sr. ×6, Alex Ross ×6, Todd McFarlane ×4, …), each card standalone. No `poster` promo_type.

---

## 5. Unobtainable rules

No rule is active. Proposals below are in `config/families.toml` as `enabled = false` rules. Proposals (pending owner review — NOT applied):

| Proposed rule | Rationale |
|---|---|
| `border_color = "black"`, tier `hard` | Catches exactly the 40 digital-only `omb` prints (only black-bordered cards in the family). Stopgap for the global digital-detection gap in §7 — the real fix is `selectors._is_digital_only` honoring Scryfall's set-level `digital` flag. |

Tier decisions pending owner review: the `mar` borderless source-material sheet (`b|sm`, 100) and the `lmar` borderless inserts (`b`, 8) are both kept by default. Recommendation: keep both (the sheet is the whole point of the set; lmar are cheap distinct-art paper promos).

**Scarcity check:** `set_status.py mar` prints no ⚠ concentration note (NON_FAMILY reporting). Manual check: `missing treatment=collectible-alt` = **$395.45 / 71 rows** (4 unpriced: lmar 5-8); top 5 = $147.96 (0.37) — Doom Variant 99 $50.64, T'Challa's Protection 51 $36.89, Parallel Lives 36 $28.16, Patriotic Shield 100 $16.88, Wolverine 97 $15.39. No scarcity tier.

Globally filtered (not MAR-specific): `serialized`, `rebalanced`/`alchemy`, arena stamp — none present here.

---

## 6. PRM destinations

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| `PRM • 000N`, Marvel Legends figure insert | `lmar` 1-8 | Hasbro Marvel Legends Series figure box insert (foil) | 1 Anti-Venom (*boosterfun*), 2 Spectacular Spider-Man, 3 Huntmaster / *Colonel John Jameson*, 4 Iron Spider, 5 Invisible Woman, 6 Captain America, Team Leader, 7 Doctor Doom, King of Latveria, 8 T'Challa, the Black Panther. Physical CN matches Scryfall CN. |

lmar 1-4 are Spider-Man characters (same oracle as `spm`/`pspm`/`om1` printings, different art); lmar 5-8 share oracle with `msc` 1/5/6/7 (+ 875/879/880/881), different art. Other Marvel PRM channels (prerelease `Ns`, `pw25` Play Promos) belong to the expansions — see [`spm.md`](spm.md) §6 and [`msh.md`](msh.md).

---

## 7. Edge cases & gotchas

- **`omb` digital leak (bug, not a family preference).** `omb` is an Arena/MTGO-only set but its cards carry no `rebalanced`/`alchemy` promo_type and no `arena` security stamp, so `selectors._is_digital_only` misses them. Verified: `set:mar+related missing` lists all 40 `omb` rows (unpriced), and `set:mar+related missing rarity=mythic treatment=regular` returns 10 `omb` mythics — i.e. the rare/mythic-regular sub-selectors of `missing-set` and the Collection view would ask the user to "buy" digital cards. The `cards` table doesn't store Scryfall's set-level `digital` flag; fix belongs in the global digital gate (or a stopgap §5 rule). Same pattern likely affects `om1` (digital, parented under `spm`).
- `arena` grep on `set:mar+related missing` → no rows (the arena-stamp path is fine; the leak is the set-level flag).
- **Duplicate names within `mar`** (Path to Exile, Counterspell, Beast Within ×2; Heroic Intervention ×4) are distinct arts — never collapse by name.
- **Name collisions with `omb`:** `omb` N has the same name as `mar` N for N=1-40 but different art and is digital.
- No meld backs, no tokens, no serialized prints.
- Owned at audit: 37 printings ($379.81) — `mar` 34 (30 in CN 1-40, 4 in 41-100), `lmar` 1/2/4.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] mar = []` — configured 2026-11-08 (enables `mm query missing-set mar`).
- `config/families.toml` `[[unobtainable.mar.rules]]` — 1 proposed rule, `enabled = false` (off until switched on).
- `config/families.toml` `[[scenes.mar]]` — none (no scenes).
- `src/magic_manager/family_status.py` `NON_FAMILY_SETS` — contains `mar` (owned-only reporting).
- `src/magic_manager/selectors.py:_is_digital_only` — the gate that misses `omb` (§7).

---

## 9. Product types

Archetypes: [`../product-types.md`](../product-types.md) (masterpiece sheet).

| Product | Archetype | Family-specific detail |
|---|---|---|
| SPM Play / Collector Boosters | masterpiece sheet | MAR 1-40 via SPM `sourceMaterial` sheets (play: nonfoil; collector: nonfoil + foil). |
| MSH Play / Collector Boosters | masterpiece sheet | MAR 41-100 via MSH `sourceMaterial` sheets (play + play-arena: nonfoil; collector: nonfoil + foil). |
| Hasbro Marvel Legends Series figures | promo insert | `lmar` 1-8, one foil card per figure box. |

**Booster types (for `sealed-value` EV):** `sealed_value.py mar --list-boosters` → "MAR: no booster data in MTGJSON." MAR has no boosters of its own — value its cards through the SPM / MSH booster EV (their `sourceMaterial` sheets).
