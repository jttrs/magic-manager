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

> **⚠️ Disambiguation — the "Marvel Jumpstart" product is `msh`, NOT this set.**
> The Marvel *Jumpstart* product is **`msh` "Marvel Super Heroes"** (`expansion`,
> 453 cards, released 2026-06-26) — a **separate family with no Scryfall link to
> `spm`** (`mm set list-related msh` roots at `msh` and never touches `spm`). It's
> the one that publishes **51 `type: Jumpstart` packs** in MTGJSON, so
> `mm set jumpstart-list msh` works. The Spider-Man family (`spm`/`spe`) publishes
> **no** Jumpstart decks (see §7), so `jumpstart-list spm`/`spe` errors with "no
> Jumpstart variants found." `msh` family topology (`mm set list-related msh`):
>
> | Code | `set_type` | Cards | Notes |
> |---|---|---:|---|
> | `msh` | expansion | 453 | Marvel Super Heroes — the Jumpstart parent |
> | `msc` | commander | 866 | Marvel Super Heroes Commander |
> | `amsh` | memorabilia | 66 | Art Series |
> | `fmsc` | memorabilia | 61 | **Jumpstart Front Cards** — the JMP front-card sheet, analogous to TLA's `jtla` |
> | `tmsh` / `tmsc` | token | 27 / 32 | set + commander tokens |
>
> MTGJSON `MSH` deck mix: 51 Jumpstart + 12 Box Set (Beginner Box) + 5 Welcome
> Deck + 2 Bundle Land Pack (archetypes: [`../product-types.md`](../product-types.md)).
> Ingest opened packs via `mm set jumpstart-list msh`
> → fill a single **`acquired_qty`** per pack (copies opened); ingest SPLITS it —
> net-new pack keeps 1 constructed + rest deconstructed, already-owned → all
> deconstructed (tracked rows) → `mm set ingest`.

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

### `mar` is its OWN cross-set masterpiece entity — NOT a Spider-Man bonus sheet (revised 2026-09-07)

**⚠️ `mar` "Marvel Universe" is NOT part of the SPM family.** It's a cross-set masterpiece
series that feeds the booster packs of MULTIPLE Marvel expansions — SPM and MSH today, plus 4
more Marvel sets to come (6 total). Like SLD/SPG span the whole game, MAR spans the Marvel block,
so it's modeled as its **own non-family anchor** (in `NON_FAMILY_SETS`, reported owned-$ only, no
Char/Missing), NOT folded into any one expansion. It was previously (mis)registered under `spm`'s
`set_targets`, which made `spm` over-claim all 100 MAR cards including the 60 that shipped with
MSH — corrected 2026-09-07.

MAR is its own small root family (`set_targets["mar"] = [mar, omb, lmar]`):

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `mar` | masterpiece | 100 | (waves) | UB reskin sheet, `sourcematerial` promo_type. **CN 1-40** (carry `boosterfun`) shipped 2025-09-26 with **SPM** boosters; **CN 41-100** (no `boosterfun`) shipped 2026-06-26 with **MSH** boosters. This CN/wave split is informational only — MAR is counted as ONE entity, not partitioned into per-family ranges (with 6 Marvel sets feeding it, per-set attribution isn't a membership the user tracks). |
| `omb` | masterpiece | 40 | 2025-09-23 | Through the Omenpaths Bonus Sheet — child of `mar` (`parent_set_code: mar`). Folds into the `mar` anchor row. |
| `lmar` | promo | 4 | 2025-09-30 | Marvel Legends Series Inserts — 4-card promo insert in Hasbro Marvel Legends figure boxes. `parent_set_code: mar`. Cards: 1 Anti-Venom (Lordigan), 2 Spectacular Spider-Man (Alex Horley-Orlandelli), 3 Huntmaster of the Fells (Mark Spears), 4 Iron Spider (Bachzim). All foil. See §6 for PRM handling. |

`mm set list-related spm` correctly does NOT include mar; `set:spm+related` and
`mm query missing-set spm` correctly exclude it. To catalog MAR, treat it as its own set:
`mm set master-list mar` (covers mar+omb+lmar). If a user asks about *Spider-Man* completion,
MAR is a SEPARATE Marvel-masterpiece checklist, not part of the SPM gap.

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

Mirrors `selectors.FAMILY_UNOBTAINABLE_RULES["spm"]` (configured 2026-09-07, user directive).

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {textured}` | The 7 Spectacular Spider-Man textured comic-panel foils (SPM 235-241, textured+boosterfun, foil-only, $199-$446 ea, ~$1,950). DISTINCT art — 7 different `illustration_id`s, a themed multi-art chase, NOT dupes of the base #14 (which is why they're correctly OUT of `FAMILY_DUPE_FOIL_PROMO_TYPES` — see §2). A fancy-foil masterpiece scarcity tier the user won't chase. |
| `collector_numbers: {243}, border_color: borderless` | The Soul Stone borderless foil (SPM 243, ~$1,839) — the family's flagship $ chase. Distinct borderless-inverted `boosterfun` art; no promo_type distinguishes it from ordinary boosterfun mythics, so pinned by CN + border_color (same technique as MSH Mind Stone 386). The base/other Soul Stone prints (om1 69, pspm 66s, spm 242) stay in scope. |

**Missing-set impact (recorded 2026-09-07):** `missing treatment=preferred` dropped from **$4,229.94 / 112 prints** → **$441.19 / 104 prints**. The ~$3,788 removed is exactly these 8 chase cards (The Soul Stone 243 ~$1,839 + the 7 textured foils ~$1,950). After the rule the list tops out at genuinely attainable prints (Eddie Brock foil 233 $143, Peter Parker foil 232 $118). This is the classic "family whose missing total is thousands has a scarcity tier" pattern flagged by the characterize-set skill.

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

- **MAR is its own cross-set masterpiece entity, NOT a Spider-Man bonus sheet** (revised 2026-09-07 — see §1). It's a `NON_FAMILY_SETS` anchor grouping `mar`+`omb`+`lmar`, spanning 6 Marvel sets. `mm set list-related spm` / `set:spm+related` / `mm query missing-set spm` all correctly exclude it. MAR is a SEPARATE checklist (`mm set master-list mar`); it is NOT part of Spider-Man completion. (Historical note: MAR was briefly folded into `spm`'s `set_targets`, which over-claimed the 60 MSH-wave MAR cards — corrected.)
- **OMB + LMAR are children of MAR** (`parent_set_code: mar`) — they fold into the `mar` anchor row, not spm.
- **`om1` is a sibling but not really Spider-Man** — Through the Omenpaths (parent expansion set_type despite being an omenpath crossover release). User excludes it from Spider-Man-specific checklists.
- **Full-art convention flip** — SPM borderless-inverted has `full_art: true` (see §2); this differs from LTR/FIN. Affects treatment audit heuristics if you're reusing FIN/LTR logic.
- **`cosmicfoil` singleton** — one print in the family. If encountered, visual-audit whether it's a dupe of another print.
- **Digital-only Arena prints** — SPM has some A-prefixed Alchemy rebalanced variants (globally filtered).
- **`headliner` and `buyabox` promo_types** — each singleton, minor edge cases.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["spm"]` — **not configured.** `mm query missing-set spm` will raise `SelectorParseError` until an entry is added. Recommended: `"spm": frozenset()` (audit shows no dupe-foil signals; empty set unblocks the query without filtering).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["spm"]` — **configured** (2026-09-07): `[{"promo_types_any_of": frozenset({"textured"})}, {"collector_numbers": frozenset({"243"}), "border_color": "borderless"}]` (the 7 textured Spectacular Spider-Man foils + The Soul Stone 243 borderless — the ~$3,788 scarcity chase tier). See §5.
- `selectors.py:_modifier_chase` — surfaces the textured Spider-Man 235–241 cluster + Gwenom + Radioactive Spider.
- `scripts/set_status.py:NON_FAMILY_SETS` — includes `mar` (its own cross-set masterpiece entity, not folded into spm); `set_targets["mar"] = [mar, omb, lmar]`, `set_targets["spm"]` no longer lists mar (corrected 2026-09-07).
- Related docs: [`../scryfall-set-families-and-bonus-sheets.md`](../scryfall-set-families-and-bonus-sheets.md) §1 (family topology + the MAR-as-cross-set-entity note), [`../scryfall-printing-treatments.md`](../scryfall-printing-treatments.md) §6.5 (full_art convention flip).
