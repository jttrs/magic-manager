# `spg` — `Special Guests`

> Per-family memory doc. Read this before answering set-specific questions about
> `spg` or working on `spg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `spg`
**Family root type:** `masterpiece`
**Family released:** 2023-11-17 → ongoing (a long-running reprint sheet, ~175 cards and growing)
**Last audit:** 2026-09-17 via `/characterize-set spg`.

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `spg` | masterpiece | 175 | 2023-11-17 → ongoing | parent — standalone, `parent_set_code: null`, no children |

**Not a Scryfall family graph.** `spg` has no `parent_set_code` and no sibling/child codes — it's a single flat masterpiece set of premium **reprints** released in waves alongside premier expansions (see §9). Despite the distributed release dates it is a **finite, completable set**, so it is treated as a normal characterized family (removed from `NON_FAMILY_SETS` on 2026-09-17). `resolve("spg")` → single-code family; `set:spg+related` = just `spg`.

No `--only` needed.

---

## 2. Treatments

`selectors.FAMILY_DUPE_FOIL_PROMO_TYPES["spg"] = frozenset({"firstplacefoil", "textured"})` (configured — see §8).

Every card has a `boosterfun` base print; the fancy tiers layer on top. Classification verified by `illustration_id` match (survey 2026-09-17):

| promo_type | Treatment | Same art as boosterfun sibling? | Handling |
|---|---|---|---|
| `boosterfun` | `b` (borderless/inverted) | — (the base representative) | KEPT — the preferred print |
| `firstplacefoil` (10) | `b\|ff` | **yes** (10/10 illustration_id match, e.g. Bone Miser 97↔87 `38893c08`) | **DUPE_FOIL** — dropped, boosterfun kept |
| `textured` (5) | `b\|ff` | **yes** (5/5 match) | **DUPE_FOIL** — dropped |
| `neonink` (6) | `b\|ff` | **no** (0/6 — distinct neon colorways of Mana Crypt) | **UNOBTAINABLE** (§5) — distinct art, won't-chase |
| `dragonscalefoil` (5) | `b\|ff` | **no** (0/5 — distinct-art fetchlands) | **UNOBTAINABLE** (§5) |
| `poster` (10) | `''` (empty) | no sibling (sole print of that card) | KEPT — distinct-art mythics, real missing cards (they surface via the mythic-regular sub-selector, which is correct here) |

**`ff`-gating check:** all four fancy tokens compute to `b|ff`, so DUPE_FOIL correctly catches the two same-art ones (`firstplacefoil`/`textured`); the two distinct-art ones (`neonink`/`dragonscalefoil`) are routed to UNOBTAINABLE instead (a DUPE_FOIL entry would wrongly drop distinct art).

---

## 3. Chase variants

None in the multi-distinct-art sense — the "variety" is base/fancy-foil tiers of one art. The premium tiers (neonink Mana Crypts, dragonscale fetchlands) are §5 exclusions, not `_modifier_chase` chase.

---

## 4. Scenes / posters / panoramas

The 10 `poster` prints (spg 119–128, borderless mythics) are individually-arted showcase panels, **not** a tiling scene set. No `FAMILY_SCENES["spg"]` entry. They are distinct art and KEPT in missing-set (they're the sole printing of those cards in the family).

---

## 5. Unobtainable rules

`selectors.FAMILY_UNOBTAINABLE_RULES["spg"]` (configured 2026-09-17):

| Rule | Rationale |
|---|---|
| `promo_types_any_of: {neonink, dragonscalefoil}` | Two DISTINCT-ART ultra-premium foil tiers (~$4,800 total) the user won't chase. **neonink**: 6 Mana Crypt neon colorways (spg 17a–d etc., foil-only, up to ~$496) — each its own illustration (0 match to the boosterfun 17), so the dupe filter would KEEP them; this rule removes them (direct analog of the fin/lci/neo neonink exclusions). **dragonscalefoil**: 5 fetchlands (spg 114–118, foil-only, $369–$594), distinct-art premium. `any_of` (the tokens never co-occur) catches exactly these 11 prints; every card's boosterfun base stays in scope. |

**Effect (owns 11/175, 2026-09-17):** `mm query missing-set spg` = **138 prints · $2,110.92**. Without the exclusions the neonink+dragonscale tiers (~$4,800) would dominate. Top of the remaining list is the boosterfun *base* prints (Chrome Mox $175, base fetchlands $44–72, base Mana Crypt $49) — real attainable reprints.

Also filtered globally (not via spg rules): `serialized` 1-of-N chase; `rebalanced`/`alchemy` digital-only (none in spg).

---

## 6. PRM destinations

N/A — spg has no prerelease/promo-pack channel (it IS the promo/masterpiece sheet). The `wizardsplaynetwork` token appears on one Mana Crypt variant (spg 17b); it's covered by the neonink exclusion.

---

## 7. Edge cases & gotchas

- **Distributed release dates.** spg's 175 cards ship in 13 waves over years (§9), each wave's `released_at` matching a premier expansion's date exactly. This is why it was initially mis-tagged NON_FAMILY — but distributed dates ≠ non-completable. It's a normal finite set.
- **Functional-missing anywhere-floor > in-family floor.** `set_status.py spg` shows functional anywhere ($3,247) HIGHER than in-family ($2,111). spg cards are premium reprints where the spg print is sometimes among the cheapest available, so the `oracleid:` anywhere search doesn't always undercut the in-family price. Not a bug — expected for a premium-reprint set.
- **No parent_set_code / block** — the companion-expansion tether (§9) is inferable only from `released_at`, and is recorded as informative metadata, NOT wired into family resolution (spg stays its own standalone set).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["spg"]` — **configured** `{firstplacefoil, textured}` (§2): same-art fancy-foil dupes.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["spg"]` — **configured** `{neonink, dragonscalefoil}` (§5): distinct-art premium tiers.
- `scripts/set_status.py:NON_FAMILY_SETS` — spg **removed** 2026-09-17 (now a normal family; `sld` remains).
- Related: `docs/spg-source-attribution.md` (the wave→expansion mapping, now surfaced in §9 here).

---

## 9. Product types

Special Guests is a premium **reprint sheet** inserted into Play/Collector boosters of premier expansions — not a standalone product with its own boosters/precons. `sealed-value` has no spg booster data (it's an insert).

**Release waves → companion expansion** (the "distributed set" structure; from `docs/spg-source-attribution.md`, verified by `released_at` == the expansion's `released_at`). Informative metadata only — spg is NOT folded into these families' missing-set/status; it stays its own set.

| CN band | `released_at` | Companion expansion |
|---|---|---|
| 1–18 | 2023-11-17 | The Lost Caverns of Ixalan (LCI) |
| 19–28 | 2024-02-09 | Murders at Karlov Manor (MKM) |
| 29–38 | 2024-04-19 | Outlaws of Thunder Junction (OTJ) |
| 39–53 | 2024-06-14 | Modern Horizons 3 (MH3) |
| 54–63 | 2024-08-02 | Bloomburrow (BLB) |
| 64–73 | 2024-09-27 | Duskmourn: House of Horror (DSK) |
| 74–83 | 2024-11-15 | Foundations (FDN) |
| 84–103 | 2025-02-14 | Aetherdrift (DFT) |
| 104–118 | 2025-04-11 | Tarkir: Dragonstorm (TDM) |
| 119–128 | 2025-08-01 | Edge of Eternities (EOE) |
| 129–148 | 2026-01-23 | Lorwyn Eclipsed (ECL) |
| 149–158 | 2026-04-24 | Avatar: The Last Airbender (TLA) |
| 159–168 | 2026-10-02 | (later wave) |

(CN bands approximate the contiguous per-wave runs; the authoritative tie is `released_at`. New waves append as future expansions ship.)
