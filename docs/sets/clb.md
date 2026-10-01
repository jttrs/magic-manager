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

CLB is a **2022, pre-fancy-foil-era** set: no fancy-foil-sheet tokens (no surgefoil / fracturefoil / halofoil / textured / neonink / etc.). ⚠️ **But do NOT read "no fancy-foil" as "nothing to filter."** WotC tags every special printing with the single `promo_types: boosterfun` umbrella token (264 prints) — the ACTUAL treatment structure lives in **`frame_effects`** and **`finishes`**, which a promo_types-only survey flattens. The real decomposition (all 936 `clb` parent cards, from the local DB):

| Treatment class | Count | CN band | Signal | `preferred` disposition |
|---|---:|---|---|---|
| **base** | 667 | 1–361 (draft) + 646–930 (deck) + 451–470 (lands) | plain black border, nonfoil/foil | computes `regular` → handled by rare/mythic/base sub-selectors, not `preferred` |
| **showcase** | 76 | 375–450 | `frame_effects: showcase` (±`legendary`), black border | **EXCLUDED (user directive, 2026-09-30)** — the UB:D&D "rulebook/module-page" showcase style the user doesn't want. `preferred` would otherwise KEEP it as treatment `shw`. See §5. |
| **extended art (set)** | 81 | 553–645 | `frame_effects: extendedart` | dropped automatically — `preferred` excludes the `ext` treatment class |
| **extended art (deck card)** | 13 | 936 band | `frame_effects: extendedart` | same — `ext`, auto-dropped |
| **etched foil** | 86 | 471–534 | `finishes: etched`, computes `b\|ff` | dropped automatically — same-art foil, collapses in the ff-dupe step |
| **borderless** | 13 | 362–374 | `border_color: borderless` | **KEPT** — the Ancient Dragons + 3 planeswalkers; the chase the user DOES want (treatment `b`/`shw`, not caught by the showcase rule's `border_color:black` guard) |

Promo-channel tokens (separate from the above): `prerelease`+`datestamped` (99 `pclb` `Ns`), `promopack`+`stamped` (5 `pclb` `Np`: 9p/63p/162p/167p/285p) — each has a `clb` base sibling so the global preferred filter drops the stamp; `thick` (4 oversized display commanders 931–934); singleton `buyabox`/`bundle`.

**Config consequence:** `FAMILY_DUPE_FOIL_PROMO_TYPES["clb"]` is an **empty frozenset** (there is genuinely no same-art fancy-foil sheet; etched collapses via the generic ff step, not a family dupe-foil entry). The showcase exclusion is a **`FAMILY_UNOBTAINABLE_RULES["clb"]`** entry — `{frame_effects_all_of: {showcase}, border_color: black}` — see §5/§8.

**Full-art convention:** standard — `full_art` TRUE only on the full-art basic lands (clb 451–467 range), FALSE elsewhere. No UB convention flip observed.

---

## 3. Chase variants

The `set:clb+related chase` (threshold 3) list surfaces **no distinct-art chase runs**. What appears is noise, not real multi-art chases:

- **Foil+nonfoil pairs** of the same CN (Battle Angels of Tyr clb 9, Displacer Kitten clb 63, the showcase planeswalkers Elminster/Minsc & Boo/Tasha 274/285/294 + their borderless 362/363/364) — counted as "2 versions" by the modifier but they are one art in two finishes, not a chase.
- **Art Series multi-prints** (aclb Ancient Gold Dragon 5/28/44 etc.) — the DFC art cards.
- **Full-art basic lands** (clb 451–467) across finishes.

`set:clb+related chase:5` returns **0 rows** — no strong-signal chase. CLB legends/dragons each print at base + showcase + (for 13) borderless, but these are the SAME art in different frames (one illustration per card), not the multi-distinct-art runs the chase modifier is built to catch. **No `uncommon-chase` tier to document.** (The borderless Dragons/planeswalkers ARE a desirable premium, but they're handled as kept `preferred` prints — see §2/§5 — not as a chase tier.)

---

## 4. Scenes / posters / panoramas

**None.** CLB has only **13 borderless cards** in `clb` (CNs 362–374: the three showcase planeswalkers + the six Ancient Dragons + Battle Angels of Tyr / Legion Loyalty / Bramble Sovereign / Nautiloid Ship / Vexing Puzzlebox). Each is a **distinct card by a distinct artist** — no contiguous same-artist run of ≥3, so no scene/panorama grouping. No `poster` promo_type exists in the family. **No `FAMILY_SCENES["clb"]` entry; `scripts/scene_table.py clb` is not applicable.**

(The Art Series `aclb` DFC cards are concept art, not borderless-inverted scene panels — they are a separate memorabilia product, not a Scryfall "Scene Cards" grouping.)

---

## 5. Unobtainable rules

**One rule configured — the D&D showcase frame is unwanted** (user directive, 2026-09-30): "the showcase style differs per set and this one is not great." The 76 showcase prints (`clb` 375–450) carry `frame_effects: showcase` (±`legendary`) and black border, and `preferred` would otherwise keep them as treatment `shw`. The rule drops them while sparing the borderless chase.

| Rule | Catches | Spares | Rationale |
|---|---|---|---|
| `frame_effects_all_of: {showcase}` + `border_color: black` | 76 showcase prints (clb 375–450) | the 13 borderless (clb 362–374: Ancient Dragons + Elminster/Minsc & Boo/Tasha — these are `border_color: borderless`, so the black guard excludes them) | UB:D&D rulebook/module showcase frame the user doesn't collect; borderless Dragons/planeswalkers ARE wanted |

**Measured effect:** `mm query missing-set clb` preferred-class rows went **88 → 12** (76 showcase removed; 10 borderless + 2 promo-pack siblings kept). The full missing-set run is 118 distinct printings / ~$1,179 (base draft + deck gaps + borderless + promo-pack stamps).

**Not excluded (handled elsewhere, no rule needed):**
- **Extended art** (set 553–645 + deck-card 936) — dropped automatically by `preferred`'s `ext`-class exclusion. The user confirmed ext is unwanted; the generic pipeline already does this.
- **Etched foil** (471–534) — computes `b|ff`, same art as its base sibling, collapses in the generic ff-dupe step.
- The 5 promo-pack `stamped` prints (`pclb` 9p/63p/162p/167p/285p) each have a non-stamped `clb` base sibling, so the global preferred filter drops the stamp (no per-family `stamped` rule needed).
- The `thick` oversized display commanders (931–934) + `oclb`/`mclb` memorabilia — not booster-obtainable singles; outside normal scope by product.

**Scarcity-concentration check:** `scripts/set_status.py clb` — CLB's priciest kept missing prints are the borderless Ancient Dragons ($17–$160) in chunk 6; no fancy-foil scarcity tier (pre-fancy-foil era). No further concentration exclusion warranted.

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

- **Draft pool vs. Commander-deck-only cards (CLB's defining structure).** The `clb` numbering splits cleanly into two non-overlapping card pools:
  - **CN 1–361** — the draftable main set (the ~361 cards that appear in Draft Boosters).
  - **CN 646–930** — **285 Commander-deck-exclusive cards** (the reprints + new cards that ship only in the 4 Commander precons / collector-booster commander slots). **Verified 0 name-overlap** with the draft pool (1–361) — these are entirely distinct cards, not alternate prints of draft cards.
  - CN 451–470 full-art basics, 471–645 the alt-treatment bands (etched/showcase/extended), 931–935 oversized/misc.

  This matters for completion math: "the set" a drafter completes (1–361) is a different target from "every card in the product" (which includes the 285 deck-only cards). Owning the 4 Commander precons (added 2026-09-30) covers the 646–930 band — which is why those show 0 missing.
- **`boosterfun` is an umbrella, not a treatment.** All 264 special prints carry `promo_types: boosterfun`; the real axis is in `frame_effects`/`finishes` (see §2). A promo_types-only audit will mis-report CLB as "one bucket, all distinct" — don't.
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
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["clb"]` — **configured** (applied 2026-09-30): one rule `{frame_effects_all_of: {showcase}, border_color: black}` excluding the 76 unwanted D&D-showcase prints (375–450) while sparing the 13 borderless. See §5.
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
