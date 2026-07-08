# `tla` — Avatar: The Last Airbender

> Per-family memory doc. Read this before answering set-specific questions about
> `tla` or working on `tla`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `tla`
**Family root type:** `expansion`
**Family released:** 2025-11-21
**Last audit:** 2026-07-08 via `survey_treatment_signature.py` + session context

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `tla` | expansion | 394 | 2025-11-21 | parent |
| `tle` | eternal | 317 | 2025-11-21 | Avatar: The Last Airbender Eternal — the Jumpstart-analog product for this family |
| `ptla` | promo | 80 | 2025-11-21 | Prerelease datestamped promos (`Ns` CNs) |
| `atla` | memorabilia | 54 | 2025-11-21 | Art Series |
| `atle` | memorabilia | 12 | 2025-11-21 | Eternal Art Series |
| `jtla` | memorabilia | 46 | 2025-11-21 | Jumpstart Front Cards |
| `ftla` | memorabilia | 10 | 2025-11-21 | Beginner Box Front Cards |
| `ttla` | token | 22 | 2025-11-21 |  |
| `ttle` | token | 2 | 2025-11-21 | Eternal tokens |

**Separately-rooted bonus sheets:** none — TLA has no equivalent to SPM's mar-not-a-child-of-spm gotcha. The `sourcematerial` reskin prints (61 total) live inside `tla` itself (CN range 297-350ish, `boosterfun+sourcematerial+universesbeyond` promo_types) rather than a separate `atla` or `xtla`-style set code.

**`mm` invocations:** default `set:tla+related` resolution works correctly.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["tla"]` — **not configured yet.** TLA's audit reveals no surgefoil / doublerainbow / silverfoil signals. `mm query missing-set tla treatment=preferred` will raise `SelectorParseError` until a config decision is made.

**Recommendation:** add `selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["tla"] = frozenset()` (empty frozenset) to satisfy the config requirement without filtering. TLA's fancy-foil signals are all unique-art per audit (neonink 4-card themed chase, raisedfoil singleton). See §8.

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `neonink` | `ff` | **no — unique art** | 4 prints (TLA 359, 360, 361, 362 — Aang, Zuko, Katara, Toph), all by Flavio Girón. This is a 4-card themed premium chase set with distinct art (different from the base-set versions of these characters). Kept. |
| `raisedfoil` | `ff` | **unknown / singleton** | 1 print: TLA 363 Avatar Aang (Bryan Konietzko), co-occurs with `headliner`. Probably a chase card with unique art; needs visual audit if the user encounters it. |
| `sourcematerial` | `sm` | n/a (part of embedded reskin sheet) | 61 prints inside `tla` itself with `boosterfun+sourcematerial+universesbeyond`. TLA's UB reskin equivalent of FIN's `fca` sheet, but not a separate set code. |
| `prerelease` + `datestamped` | (base treatment) | **yes** → global `preferred` filter drops these | 80 ptla `Ns` prints. Handled by the `preferred`-mode datestamped-sibling filter. |
| `headliner` | (attached to raisedfoil) | n/a | Singleton on TLA 363. |
| `buyabox` | (special promo) | n/a | Singleton, standard buyabox promo. |
| `bundle` | (special promo) | n/a | Singleton, standard bundle promo. |

**Full-art convention:** TLA follows the newer UB convention — borderless-inverted cards have `full_art: true` (like SPM). See `docs/scryfall-printing-treatments.md` §6.5.

---

## 3. Chase variants

Detected by `selectors._modifier_chase` (default threshold 3).

**No uncommon multi-variant chase** in TLA analogous to LTR Nazgûl or FIN Cid. `mm query missing-set tla rarity=uncommon treatment=regular chase` returns zero rows.

The chase filter surfaces:
- **Momo, Friendly Flier** — 3 prints (ptla 29s + tla 29 + tla 394), spans 3 treatments (base, prerelease, buyabox variant). Not a single-treatment chase like Cid.
- **Flavio Girón neonink 4-set** (§2 above) — Aang/Zuko/Katara/Toph at TLA 359-362. Each has a same-name base-set sibling (TLA 4/220/N/N), so `chase` counts these together as a 2-print chase per name, below threshold 3.
- **Basic-land common CNs** (Plains, Mountain, etc.) hit chase threshold naturally since sets always ship multiple basic-land arts. Not a shopping target — sealed product provides these.

---

## 4. Scenes / posters / panoramas

**Not yet audited.** TLA is a large family (394 cards in parent, 317 in tle) so scene detection is worth running. Apply the LTR scene-detection recipe (`docs/sets/ltr.md` §4a) to TLA if a scene-completion question comes up.

Candidate signal areas:
- **`sourcematerial` reskin prints** (61 in `tla`, around CN 297-350) may include thematic groupings analogous to LTR 399-451.
- **`atla` Art Series** (54 cards) is a memorabilia set — not spatial "scenes" but a themed art collection.

Update this section when a scene audit runs.

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["tla"]` — not configured. No LTR-style scroll-frame equivalent surfaced yet.

Globally filtered:
- `serialized` promo_type.
- `rebalanced` / `alchemy` promo_types (TLA has A-prefixed Arena rebalances).

---

## 6. PRM destinations

TLA's PRM-stamped physical promo cards can land in these Scryfall set codes:

| Physical stamp | Scryfall set | Channel | Example |
|---|---|---|---|
| Prerelease datestamped, CN `Ns` | `ptla` | Set prerelease | Aang `ptla` 203s, Aang's Iceberg `ptla` 5s |
| Play Promo, small CN | `pw25` (if within release window) or `pw26` | WPN Play Promo | e.g. pw25 14 Gran-Gran (Mizutametori) |
| Bundle promo | inside `tla` (CN 393 Firebending Student, `buyabox` promo_type) | In-set bundle | Not a `p*` set. |

For any PRM-stamped TLA card, resolve by name+artist per `.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **`tle` (Avatar: The Last Airbender Eternal) is `set_type: eternal`, not `set_type: commander`.** Similar to TMT's `tmc`. Contains a Jumpstart-analog product with 317 cards.
- **`jtla` "Jumpstart Front Cards"** (46 memorabilia) — a separate memorabilia set for Jumpstart product front cards. Different from the actual Jumpstart cards in tle.
- **`ftla` "Beginner Box Front Cards"** (10 memorabilia) — similar; front cards from the beginner box product.
- **Digital-only Arena prints** — TLA has A-prefixed Alchemy rebalanced variants (globally filtered).
- **Full-art convention flip** — TLA borderless-inverted has `full_art: true` (see §2); this differs from LTR/FIN.
- **Embedded reskin sheet** — 61 `sourcematerial` prints inside `tla` (not a separate set code like FIN's `fca` or SPM's `mar`). Discriminator is the promo_type, not a set code check.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["tla"]` — **not configured.** Recommended: `"tla": frozenset()` (audit shows no dupe-foil signals; empty set unblocks `missing-set` queries).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["tla"]` — not configured (no rule needed).
- `selectors.py:_modifier_chase` — chase variants surface via `mm query missing-set tla`.
- Related docs: [`../scryfall-printing-treatments.md`](../scryfall-printing-treatments.md) §6.5 (full_art convention).
