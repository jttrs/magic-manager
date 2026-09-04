# `acr` — Assassin's Creed

> Per-family memory doc. Read this before answering set-specific questions about
> `acr` or working on `acr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `acr`
**Family root type:** `draft_innovation` (a Universes Beyond "Beyond" booster set — like the earlier UB releases, not `expansion`)
**Family released:** `2024-11-05`
**Last audit:** `2026-09-03` via `/characterize-set acr`.

---

## 1. Family map

4 Scryfall codes, all linked via `parent_set_code` (clean graph). A compact UB
set — no Commander/promo-pack siblings.

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `acr` | draft_innovation | 309 | 2024-11-05 | parent — the "Beyond Booster" UB set |
| `aacr` | memorabilia | 20 | 2024-11-05 | Art Series |
| `macr` | minigame | 3 | 2024-11-05 | **Minigames** — 3 punch-out/minigame cards (unusual `minigame` set_type) |
| `tacr` | token | 8 | 2024-11-05 | tokens |

`mm set master-list acr` / `set:acr+related` resolve the whole family from the
parent. Every card is `universesbeyond` (306/306). **No promo set** (`pacr`) —
no prerelease/promo-pack channel; the only promos are the single `buyabox`
(Hidden Blade 307) and `bundle` (Royal Assassin 306) inserts inside `acr`.

**Sync note:** `mm set sync acr` pulls the parent (309). The whole family is 306
value-bearing prints after resolving related.

---

## 2. Treatments

| promo_type | Treatment keyword | Dupe of a sibling? | Notes |
|---|---|---|---|
| `boosterfun` | `b` / `shw` / `ext` (frame-dependent) | n/a (structural) | showcase (`showcase`), borderless-inverted (`b`), etched (`inverted,etched`) frames; KEPT. Many legends have base + inverted + etched + showcase tiers |
| `textured` (+`boosterfun`) | `shw\|ff` | **yes → `FAMILY_DUPE_FOIL_PROMO_TYPES`** | ACR 267-271 — the 5 protagonist textured foils (Ezio 267, Altaïr 268, Edward 269, Eivor 270, Kassandra 271), foil-only, $15-$60. Each shares its `illustration_id` with a `showcase` sibling (Ezio 267↔131 `42171712`, Altaïr 268↔137 `c99db07c`, …) — same art, textured-foil sheet. Both key to `{shw}` (textured adds `ff`), so the sibling dedup pairs them cleanly. Drops the textured, keeps the showcase |
| `serialized` + `doublerainbow` (+`boosterfun`) | `shw\|ff` | scarcity → dropped by GLOBAL filter | ACR 120z Mary Read and Anne Bonny — the family's headline serialized chase, foil-only, ~$600. `serialized` is in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so it never reaches missing-set. §5 lists a documented no-op rule for parity |
| `buyabox` | `''` | promo | ACR 307 Hidden Blade — buy-a-box promo. Singleton |
| `bundle` | `''` | promo | ACR 306 Royal Assassin — bundle promo. Singleton |

**Full-art convention:** standard (borderless/showcase carry `border_color:
borderless` or `frame_effects: showcase`/`inverted`; `full_art` not relied upon).

---

## 3. Chase variants

**None** by the `chase` modifier (0 rows) — no card name has ≥3 distinct-art
printings at the same `(name, treatment)`. The set's variety is base/inverted/
etched/showcase tiers of *different* legends, not multi-art of one card. (The 5
protagonists each have base + showcase + etched + textured, but those are
different treatments of the same art, not distinct arts.)

---

## 4. Scenes / posters / panoramas

**None.** The borderless-inverted block (ACR 111-126) leads with the
horizonlands cycle (111-116 Sunbaked Canyon … Waterlogged Grove, all Alexander
Gering — a canonical **land cycle**, not a narrative scene), then scatters across
individual artists (117+ Capitoline Triad, Leonardo da Vinci, Cleopatra, Mary
Read, …). No single-artist contiguous narrative run ≥3 beyond the land cycle.
Not encoded in `FAMILY_SCENES`.

---

## 5. Unobtainable rules

Mirrors `FAMILY_UNOBTAINABLE_RULES["acr"]` in `src/magic_manager/selectors.py`.

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {serialized, doublerainbow}` | ACR 120z Mary Read and Anne Bonny (serialized + doublerainbow, foil-only, ~$600) — the family's headline ultra-rare. **Documented no-op:** `serialized` is already in the GLOBAL `UNOBTAINABLE_PROMO_TYPES`, so 120z is filtered before this rule applies (verified: identical result with and without it). Kept for parity/discoverability with the INR/ECL/SOS headliner families |

No `stamped` promo-pack tier (no `pacr` promo set exists). The `buyabox`/`bundle`
singletons are distinct promos the user may want — NOT excluded.

**Missing-set impact (recorded 2026-09-03):** with the DUPE_FOIL `{textured}`
config, `missing-set acr` goes from **114 prints / ~$601** (empty config) to
**109 prints / ~$412**. The ~$189 drop is the 5 textured protagonist foils. Top
by value after config: normal chase cards (Sword of Feast and Famine 124 ~$48,
Ezio 113 ~$28, Excalibur 72 ~$19) — a clean list, no scarcity tier.

---

## 6. PRM destinations

**None.** Assassin's Creed shipped with **no prerelease/promo-pack channel** —
there is no `pacr` set, no `Ns`/`Np` stamped promos. The only in-family promos
are the `buyabox` (Hidden Blade, `acr` 307) and `bundle` (Royal Assassin, `acr`
306) inserts, both filed under `acr` itself. If a user presents a "PRM"-stamped
Assassin's Creed card, resolve it by name+CN within `acr`.

---

## 7. Edge cases & gotchas

- **Parent `set_type` is `draft_innovation`** (in `DEFAULT_INVENTORY_SET_TYPES`?
  No — that frozenset is {expansion, commander, masterpiece, promo, eternal}).
  But the anchor is always included by `filtered_codes()` regardless, so `acr`
  itself is in scope; `aacr` (memorabilia), `macr` (minigame), `tacr` (token) are
  excluded by default — opt in via `--include memorabilia,minigame,token`.
- **`macr` (minigame)** is an unusual `set_type`: 3 punch-out Assassin's Creed
  minigame cards, not normal Magic cards. Excluded from the default bundle.
- **No arena leak** — `set:acr+related missing | grep arena` returns nothing
  (verified); no alchemy child (paper-only UB set).
- **Every card is `universesbeyond`** — the survey shows 306/306. This is a fully
  reskinned UB set; there are no "canonical Magic name" reprints to merge (unlike
  FCA/MAR reskins where flavor_name ≠ oracle_name), though a few reprints
  (Swords, Black Market Connections, Surtr) keep their Magic identity.

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["acr"]` — **configured**: `frozenset({"textured"})` (5 protagonist textured foils dupe their showcase siblings).
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["acr"]` — **configured** (documented no-op): `[{"promo_types_any_of": frozenset({"serialized", "doublerainbow"})}]` (Mary Read 120z, already caught by the global filter; kept for parity).
- `FAMILY_SCENES["acr"]` — not configured (land cycle, no narrative scene; see §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific specifics:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Assassin's Creed Art Series | Art Series | `aacr` (20 cards) |
| Assassin's Creed Minigames | (minigame — novel) | `macr` (3 punch-out minigame cards); unusual `minigame` set_type |
| Buy-a-Box / Bundle promos | Buy-a-Box / Bundle | Hidden Blade (`acr` 307, buyabox), Royal Assassin (`acr` 306, bundle) — filed in `acr`, no separate promo set |
| — (no Commander / precon products) | — | A Beyond-Booster UB set; no sealed precon/deck products, no promo channel |
