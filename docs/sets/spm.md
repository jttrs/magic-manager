# `spm` — Marvel's Spider-Man

> Per-family memory doc. Read this before answering set-specific questions about
> `spm` or working on `spm`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `spm`
**Family root type:** `expansion`
**Family released:** 2025-09-26
**Last audit:** 2026-07-08 via `survey_treatment_signature.py` + session context

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `spm` | expansion | 286 | 2025-09-26 | parent — includes textured Spectacular Spider-Man comic-panel series (SPM 235–241) |
| `spe` | eternal | 26 | 2025-09-26 | Marvel's Spider-Man Eternal — the ~Jumpstart-analog product for this family |
| `pspm` | promo | 68 | 2025-09-26 | Prerelease datestamped promos (`Ns` CNs) |
| `aspm` | memorabilia | 54 | 2025-09-26 | Art Series |
| `tspm` | token | 7 | 2025-09-26 |  |
| `om1` | expansion | 189 | 2025-09-23 | **Through the Omenpaths** — sibling release, shares release window; despite `set_type: expansion` and `parent_set_code: spm` it's NOT strictly a Spider-Man set (crossover title). Whether to include in a Spider-Man checklist is a per-user choice — the user's canonical Spider-Man checklist uses `--only spm,pspm,spe` and excludes OM1. |

### Separately-rooted bonus sheets (linked to SPM by product but not by Scryfall)

**⚠️ `mar` "Marvel Universe" is a separately-rooted Spider-Man bonus sheet.** Scryfall lists `parent_set_code: null`, so `mm set list-related spm` does NOT include it. The user's canonical Spider-Man collection needs it added explicitly via `--only`.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mar` | masterpiece | 100 | 2025-09-26 | UB reskin sheet with `sourcematerial` promo_type. This is the Marvel-Universe-to-MtG reskin equivalent of FIN's `fca` or TMT's `pza`. |
| `omb` | masterpiece | 40 | 2025-09-23 | Through the Omenpaths Bonus Sheet — **child of `mar`, not of `spm`**. `parent_set_code: mar`. |
| `lmar` | promo | 4 | 2025-09-30 | Marvel Legends Series Inserts — 4-card promo insert sold inside Hasbro Marvel Legends action figure boxes. Also separately rooted. Cards: 1 Anti-Venom (Lordigan), 2 Spectacular Spider-Man (Alex Horley-Orlandelli), 3 Huntmaster of the Fells (Mark Spears), 4 Iron Spider (Bachzim). All foil. See `docs/sets/spm.md` §6 for PRM handling. |

**`mm` invocations that need `--only`:**

```bash
# Include the Marvel Universe bonus sheet
mm set master-list spm --only spm,pspm,spe,mar

# Include everything Spider-Man-adjacent (including OM1 + all bonus sheets)
mm set master-list spm --only spm,pspm,spe,om1,mar,omb,lmar
```

Fix landed in `751e627` predecessor commit — `_resolve_codes` now honors `--only` codes verbatim even when they're outside the parent's related-set graph.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["spm"]` — **not configured yet.** SPM's audit reveals no surgefoil / doublerainbow / chocobotrackfoil / silverfoil signals (per `survey_treatment_signature.py SPM`). `mm query missing-set spm treatment=preferred` will raise `SelectorParseError` until a config decision is made.

**Recommendation:** add `selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["spm"] = frozenset()` (empty frozenset) to satisfy the config requirement without filtering anything. SPM's fancy-foil signals are all unique-art (textured comic panels 235–241, singleton cosmicfoil), so there's nothing to filter. See §8.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `textured` | `ff` | **no — unique art** | SPM 235–241 (7 prints) are **7 distinct comic-panel arts** of Spectacular Spider-Man, each a different scene from Roberta Ingranata's cover series. Not dupes. See §3 chase table. |
| `cosmicfoil` | `ff` | **unknown** | Singleton in the family. Needs visual audit if the user encounters it — could be a unique-art bonus print (kept) or same-art fancy foil (dupe). |
| `sourcematerial` | `sm` | n/a (part of MAR masterpiece sheet) | Discriminator for `mar` (100 cards) and `omb` (40 cards) reskin sheets. Both have borderless full-art + `flavor_name` often populated. |
| `poster` | (implicit `b`+`shw`) | mixed | SPM 221–229 posters have same-art base-set siblings — filtered by the standard poster→base-set matching in the missing-set pipeline. |
| `prerelease` + `datestamped` | (base treatment) | **yes** → global `preferred` filter drops these | 68 pspm `Ns` prints, each with a base-set sibling without the stamp. Handled by the `preferred`-mode datestamped-sibling filter (`cli.py:2227`). |

**Full-art convention:** SPM follows the newer UB convention — borderless-inverted cards have `full_art: true` (unlike LTR/FIN which have `full_art: false`). See `docs/scryfall-printing-treatments.md` §6.5.

---

## 3. Chase variants

Detected by `selectors._modifier_chase` (default threshold 3).

| Card name | Count | CN range | Rarity | Treatment |
|---|---:|---|---|---|
| Spectacular Spider-Man (textured comic panels) | 7 | `spm` 235–241 | rare | ff (textured) |
| Gwenom, Remorseless | 2 | `spm` 56, 286 | mythic | regular + ff |
| Radioactive Spider | 3 | `spm` 111, 212, 285 + `pspm` 111s | rare | regular + b + ff (bundle) |

**No uncommon multi-variant chase** in SPM analogous to LTR Nazgûl or FIN Cid. The `mm query missing-set spm rarity=uncommon treatment=regular chase` sub-selector returns zero rows.

The **7-print Spectacular Spider-Man textured series** is the SPM chase story: 7 comic panels by Roberta Ingranata (SPM 235–241) at ~$200–$400 each foil. Very expensive to complete.

---

## 4. Scenes / posters / panoramas

**Jim Cheung & Jay David Ramos borderless-inverted cover run** at SPM 199–207 + 216 (10 CNs total, some interruption at 208–215 by other artists). This is a spider-verse-themed cover art series but doesn't cleanly satisfy the strict "contiguous CN + single artist" scene heuristic. Not currently modeled as a scene.

**SPM poster prints** at CN 221–229 (17 total across the poster series). Each has both non-serialized and serialized twins; serialized filtered globally. Not analogous to LTR's 731–750 5-card-per-poster tiling — SPM posters are individual cards, not multi-panel tilings.

**No verified 5-card-per-scene grouping** in SPM comparable to LTR 399–451.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["spm"]` — not configured. No LTR-style scroll-frame equivalent surfaced yet.

Globally filtered (not SPM-specific):
- `serialized` promo_type.
- `rebalanced` / `alchemy` promo_types.

---

## 6. PRM destinations

SPM's PRM-stamped physical promo cards can land in these Scryfall set codes. **The physical CN often DOES NOT match the Scryfall CN** — the printed `PRM • 0002` and `PRM • 0004` low CNs correspond to Scryfall's `pw25` CNs 10-13 (WPN Play Promo sequence) or `lmar` 1-4 (Marvel Legends insert sequence).

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| Prerelease datestamped, CN `Ns` | `pspm` | Set prerelease | Anti-Venom `pspm` 1s |
| `PRM • 000N` low CN, Play Promo tag | `pw25` (CNs 10, 11, 12, 13) | WPN Play Promo | Spider-Ham, Mary Jane Watson, Ultimate Green Goblin, Carnage — physical CN 0002/0003/0004/0005 → Scryfall pw25 10/13/11/12 |
| `PRM • 000N` low CN, Marvel Legends insert | `lmar` (CNs 1–4) | Hasbro Marvel Legends action figure inserts | Anti-Venom `lmar` 1, Spectacular SM `lmar` 2, Iron Spider `lmar` 4. Physical CN matches Scryfall CN for lmar. |
| Bundle promo, CN 285 | `spm` 285 | In-set bundle promo | Radioactive Spider (Toni Infante), foil-only. Not a `p*` set, sits in the main set. |

**Resolution recipe:** for any PRM-stamped SPM card, resolve by name+artist via `scryfall.sh search '<name>' unique=prints` and cross-reference the artist against the tables here (Paolo Rivera + WPN → pw25; Lordigan/Alex Horley-Orlandelli/Bachzim → lmar). Never query `set:prm` — that's MTGO digital-only.

---

## 7. Edge cases & gotchas

- **MAR is separately rooted** — the single biggest gotcha. `mm set list-related spm` does NOT list mar; `set:spm+related` selectors do NOT include mar cards; `mm query missing-set spm` does NOT check for missing mar cards. The user's canonical Spider-Man checklist adds mar via `--only spm,pspm,spe,mar`. If a user asks about Spider-Man completion, always mention MAR explicitly.
- **OMB is child of MAR** — Through the Omenpaths Bonus Sheet is `parent_set_code: mar`. It's transitively "in the SPM family" via product association but Scryfall's graph splits it under mar.
- **`om1` is a sibling but not really Spider-Man** — Through the Omenpaths (parent expansion set_type despite being an omenpath crossover release). User excludes it from Spider-Man-specific checklists.
- **Full-art convention flip** — SPM borderless-inverted has `full_art: true` (see §2); this differs from LTR/FIN. Affects treatment audit heuristics if you're reusing FIN/LTR logic.
- **`cosmicfoil` singleton** — one print in the family. If encountered, visual-audit whether it's a dupe of another print.
- **Digital-only Arena prints** — SPM has some A-prefixed Alchemy rebalanced variants (globally filtered).
- **`headliner` and `buyabox` promo_types** — each singleton, minor edge cases.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["spm"]` — **not configured.** `mm query missing-set spm` will raise `SelectorParseError` until an entry is added. Recommended: `"spm": frozenset()` (audit shows no dupe-foil signals; empty set unblocks the query without filtering).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["spm"]` — not configured (no rule needed).
- `selectors.py:_modifier_chase` — surfaces the textured Spider-Man 235–241 cluster + Gwenom + Radioactive Spider.
- Related docs: [`../scryfall-set-families-and-bonus-sheets.md`](../scryfall-set-families-and-bonus-sheets.md) §1 (family topology, mentions mar-not-a-child-of-spm at line 60), [`../scryfall-printing-treatments.md`](../scryfall-printing-treatments.md) §6.5 (full_art convention flip).
