# `clb` — `Commander Legends: Battle for Baldur's Gate`

> Per-family memory doc. Read this before answering set-specific questions about
> `clb` or working on `clb`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `clb`
**Family root type:** `draft_innovation` (a Commander-focused draftable set — the Commander Legends line, like `cmr`; NOT a plain `expansion`)
**Family released:** 2022-06-10 (Universes Beyond: Dungeons & Dragons — Baldur's Gate)
**Last audit:** 2026-09-30 via `/characterize-set clb`.

---

## 1. Family map

Resolved via `mm set list-related clb`. All six codes are synced locally.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `clb` | draft_innovation | 936 | 2022-06-10 | parent; CNs 1–934 (base + boosterfun showcase/borderless + 931–934 oversized `thick`) |
| `pclb` | promo | 104 | 2022-06-10 | 99 prerelease `Ns` (`prerelease`+`datestamped`) + 5 promo-pack `Np` (`promopack`+`stamped`) |
| `aclb` | memorabilia | 81 | 2022-06-10 | Art Series (DFC art cards, no promo_types, no signed/`s` chase) |
| `mclb` | minigame | 3 | 2022-06-10 | the 3 minigame cards (Roll for Initiative / Mimic Match / Mini-Master) |
| `oclb` | memorabilia | 1 | 2022-06-10 | single oversized "Undercity // The Initiative" dungeon card (CN 20) |
| `tclb` | token | 51 | 2022-06-10 | tokens/emblems (tracked, but never in missing-set — see `CLAUDE.md` token section) |

Topology is **cleanly rooted** — every sibling's `parent_set_code` traces back to `clb`. **No separately-rooted bonus sheet** (unlike SPM↔`mar`). No `--only` incantation needed; `set:clb+related` resolves the whole family.

**`mm` invocations:**

```
mm set master-list clb          # whole family via normal resolve
mm query missing-set clb        # once DUPE_FOIL is configured (see §8)
```

---

## 2. Treatments

CLB is a **2022, pre-fancy-foil-era** set. The `scripts/survey_treatment_signature.py CLB` audit (2026-09-30) found **NO fancy-foil-sheet tokens at all** — no surgefoil / fracturefoil / halofoil / textured / neonink / etc. The complete `promo_types` frequency across the 1176 family prints:

| promo_type | Count | Treatment keyword | Dupe of a sibling? | Notes |
|---|---:|---|---|---|
| `boosterfun` | 264 | `b` / `ext` / `shw` | **no — distinct art** | the showcase + borderless + extended-art legends/dragons. KEPT (preferred representatives). |
| `prerelease` | 99 | (stamped) | — | the 99 `pclb` `Ns` datestamped prerelease promos (co-occurs with `datestamped`). |
| `datestamped` | 99 | (stamped) | — | always paired with `prerelease` (99 co-occurrences). Global preferred filter drops stamped vs. the clb base sibling. |
| `promopack` | 5 | (stamped) | — | the 5 `pclb` `Np` promo-pack cards (9p/63p/162p/167p/285p); co-occur with `stamped`; each has a clb base sibling. |
| `stamped` | 5 | (stamped) | — | same 5 promo-pack prints. |
| `thick` | 4 | — | — | the 4 oversized display commanders (clb 931–934); not booster-obtainable singles. |
| `buyabox` | 1 | — | — | singleton buy-a-box promo. |
| `bundle` | 1 | — | — | singleton bundle promo. |

**No DUPE_FOIL entry is needed to describe actual dupes** — there is no same-art fancy-foil sheet in this family. But `treatment=preferred` / `mm query missing-set` still **refuse to run** until the family has a (possibly empty) `FAMILY_DUPE_FOIL_PROMO_TYPES["clb"]` entry. Propose an **empty frozenset** (the TLA/SPM/SOS/VOW/C21/NEO pattern) to unblock the preferred filter without dropping anything. See §8.

**Full-art convention:** standard — `full_art` TRUE only on the full-art basic lands (clb 451–467 range), FALSE elsewhere. No UB convention flip observed.

---

## 3. Chase variants

The `set:clb+related chase` (threshold 3) list surfaces **no distinct-art chase runs**. What appears is noise, not real multi-art chases:

- **Foil+nonfoil pairs** of the same CN (Battle Angels of Tyr clb 9, Displacer Kitten clb 63, the showcase planeswalkers Elminster/Minsc & Boo/Tasha 274/285/294 + their borderless 362/363/364) — counted as "2 versions" by the modifier but they are one art in two finishes, not a chase.
- **Art Series multi-prints** (aclb Ancient Gold Dragon 5/28/44 etc.) — the DFC art cards.
- **Full-art basic lands** (clb 451–467) across finishes.

`set:clb+related chase:5` returns **0 rows** — no strong-signal chase. CLB legends/dragons each print at base + one or two boosterfun treatments (showcase + borderless), which is below the distinct-art chase bar. **No `uncommon-chase` tier to document.**

---

## 4. Scenes / posters / panoramas

**None.** CLB has only **13 borderless cards** in `clb` (CNs 362–374: the three showcase planeswalkers + the six Ancient Dragons + Battle Angels of Tyr / Legion Loyalty / Bramble Sovereign / Nautiloid Ship / Vexing Puzzlebox). Each is a **distinct card by a distinct artist** — no contiguous same-artist run of ≥3, so no scene/panorama grouping. No `poster` promo_type exists in the family. **No `FAMILY_SCENES["clb"]` entry; `scripts/scene_table.py clb` is not applicable.**

(The Art Series `aclb` DFC cards are concept art, not borderless-inverted scene panels — they are a separate memorabilia product, not a Scryfall "Scene Cards" grouping.)

---

## 5. Unobtainable rules

**None proposed.** The audit surfaced no scarcity tier the user would rule out:

- The 5 promo-pack `stamped` prints (`pclb` 9p/63p/162p/167p/285p) each have a **non-stamped clb base sibling** in the family graph, so the **global** preferred filter (which drops `stamped`/`promopack` when a non-stamped sibling exists) handles them — unlike SNC/EOE/ECL where the stamped promos had no in-family base sibling and needed an explicit `promo_types_any_of: {stamped}` rule. Here only 5 prints and all paired, so no per-family `stamped` rule is warranted.
- No fancy-foil masterpiece/galaxyfoil/headliner tier exists (pre-fancy-foil era).
- The `thick` oversized display commanders (clb 931–934) and the `oclb`/`mclb` memorabilia are not booster-obtainable singles; they fall outside normal missing-set scope by rarity/product, not needing a taste rule.

**Scarcity-concentration check:** `scripts/set_status.py clb` could **not** compute a missing-$ figure (missing requires `treatment=preferred`, which is unconfigured), so the `⚠ missing $ concentrated` note did not fire. Once the empty-DUPE_FOIL entry (§8) lands, re-run `set_status.py clb`; CLB's priciest missing prints are low-dollar ($30-ish Displacer Kitten / Battle Angels showcases), so no concentration exclusion is anticipated. **No before/after missing total recorded** (family not yet configured).

| Rule | Rationale |
|---|---|
| *(none)* | 2022 set, no fancy-foil chase, promo-pack stamps handled by the global filter via their in-family base siblings. |

---

## 6. PRM destinations

For the "I have a PRM-stamped CLB card" flow ([[bulk-add]] skill). `.claude/skills/bulk-add/SKILL.md` has **no CLB-specific mention** — nothing to carry over; this section is the first record.

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` (e.g. `264s`, `274s`) | `pclb` | Prerelease datestamped (`prerelease`+`datestamped`) | Alaundo the Seer `264s` → `pclb` 264s; Elminster `274s` → `pclb` 274s |
| `Np` (e.g. `162p`, `285p`) | `pclb` | Promo Pack (`promopack`+`stamped`) | Balor `162p` → `pclb` 162p; Minsc & Boo `285p` → `pclb` 285p (only 5 exist: 9p/63p/162p/167p/285p) |

Both promo channels live in the single `pclb` set (CLB has no `pw22`/showdown/regional sibling in-family). The physical `Ns`/`Np` CN mirrors the main-set CN of the same card — resolve by name and read the Scryfall CN off the `pclb` match.

---

## 7. Edge cases & gotchas

- **Family root is `draft_innovation`, not `expansion`.** CLB is a draftable Commander product (the Commander Legends line). Any code that keys on `set_type == "expansion"` must account for this.
- **`thick` oversized display commanders** (clb 931–934: Captain N'ghathrod, Faldorn, Firkraag, Nalia de'Arnise) — oversized stock, not booster singles. Each has a normal base/boosterfun print at a lower CN.
- **`oclb` single oversized card** — "Undercity // The Initiative" (CN 20), the oversized dungeon card. `set_type: memorabilia`.
- **`mclb` minigame cards** (CNs 1–3) — the pack-wrapper minigames (Roll for Initiative / Mimic Match / Mini-Master), `set_type: minigame`. Not real playable singles.
- **`aclb` Art Series** (81 DFC art cards) — `set_type: memorabilia`, no promo_types, and (verified) **no signed/gold-stamped `s`-suffix serialized chase** in this family's art cards.
- **No digital-only / Arena leak** — `set:clb+related missing treatment=collectible-alt` returns zero `arena`-stamped rows (confirmed clean; `_is_digital_only` not implicated).
- **No name collisions** of concern across siblings beyond the normal base↔boosterfun↔prerelease multi-prints of the same card.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["clb"]` — **configured: empty `frozenset()`** (applied 2026-09-30). Unblocks `treatment=preferred` / `mm query missing-set clb`; drops nothing (no fancy-foil dupe exists). Mirrors TLA/SPM/SOS/VOW/C21/NEO.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["clb"]` — **not configured; none needed** (promo-pack stamps handled by the global filter; no scarcity tier).
- `selectors.FAMILY_SCENES["clb"]` — **not configured; N/A** (no scenes).
- Related test data: none.

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md). CLB specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| 4 Commander Decks | Commander deck | `Draconic Dissent`, `Exit from Exile`, `Mind Flayarrrs`, `Party Time` — the only real decklists in the set file. All four are in the collection (slugs `draconic-dissent` / `exit-from-exile` / `mind-flayarrrs` / `party-time`). MTGJSON `type: Commander Deck`. "Commander Decks Set of 4" and per-deck "Minimal Packaging" are sealed SKUs around the same decklists. |
| Bundle Land Pack | Bundle component | MTGJSON deck `Commander Legends: Battle for Baldur's Gate Bundle Land Pack` (`type: Bundle Land Pack`) — the land pack inside the Bundle, basics only. |
| Art Series | Art Series | `aclb` (81 DFC art cards); handle as memorabilia, not booster EV. |
| Oversized / minigame | memorabilia / minigame | `oclb` (1 oversized), `mclb` (3 minigame), clb 931–934 `thick` display commanders — not standard singles. |

**Booster types (for `sealed-value` EV)** — enumerated via `scripts/sealed_value.py clb --list-boosters` (2026-09-30):

| Booster type | EV | Coverage | Notes (what MTGJSON can't say) |
|---|---:|---:|---|
| `collector` | $49.91 | 82.6% | Collector Booster — the premium configuration. |
| `collector-sample` | $9.74 | 97.8% | the Collector Booster Sample Pack. |
| `draft` | $16.66 | 91.5% | Draft Booster — the "3 Booster Draft Pack" / Draft Booster Box config. |
| `prerelease` | $9.20 | 95.5% | Prerelease Pack contents. |
| `set` | $14.61 | 88.5% | Set Booster. |

Coverage sits 82–98% — the un-covered slices are the datestamped prerelease / promo-pack sheet cards that live in `pclb` (all synced). No glaring EV gap; no unsynced child set to chase. The 4 Commander Decks are **fixed decklists → value as decks (`import-precon` / `construct-value`), not booster EV.**
