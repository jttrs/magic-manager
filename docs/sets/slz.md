# `slz` — `The Zeta Set` (Secret Lair x MSCHF)

> Per-family memory doc. Read this before answering set-specific questions about
> `slz` or working on `slz`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `slz`
**Family root type:** `box` (a Secret Lair-subtype booster product, not an expansion)
**Family released:** 2026-09-02
**Last audit:** 2026-11-01 via `/characterize-set slz` (batch run; tier decisions pending owner review).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `slz` | box | 363 | 2026-09-02 | parent — standalone, `parent_set_code: null`, no children |

**What it is.** MTGJSON's only sealed product is *"Secret Lair x MSCHF - The Zeta Set Booster Pack"* (`category: booster_pack`, `subtype: secret_lair`). It is a randomized booster product of **121 reprints × 3 versions = 363 prints**, every print credited to artist `MSCHF`, all `full_art: true`, black border, `frame: 2015`, nonfoil only, `security_stamp: oval`, `promo_types: null`, `booster: false` on Scryfall. Tournament-legal reprints (commander/legacy/vintage/modern legal, e.g. Dispatch); 6 cards are vintage-restricted (Brainstorm, Dig Through Time, Mental Misstep, Merchant Scroll, Sol Ring, Windfall).

**Version layout (CN bands).** The same 121-card list repeats three times in identical order — CN `N`, `N+121`, `N+242` are the same card (e.g. Dispatch = 2 / 123 / 244; Chrome Mox mythic in each band; Oboro = 361 in v3). All 363 have **distinct `illustration_id`s**, so each version is distinct art, not a dupe.

| Band | CNs | Pack frequency (MTGJSON weights) |
|---|---|---|
| v1 | 1–121 | ~85% (weight 17 / 51 / 34 on the C-U / rare / mythic sheets) |
| v2 | 122–242 | ~10% (weight 2 / 6 / 4) |
| v3 | 243–363 | ~5% (weight 1 / 3 / 2) |

Per band: 52 common, 39 uncommon, 20 rare, 10 mythic. Scryfall rarity is identical across the three versions of a card — **version scarcity is NOT encoded in `rarity` or any promo_type, only in CN band + booster weights.**

No separately-rooted bonus sheet (checked Scryfall `/sets` 2026-08-15 → 2026-09-30: `slz` is the only set in the window). No `--only` needed; `set:slz+related` = just `slz`.

---

## 2. Treatments

Uniform: every one of the 363 prints computes to treatment **`fa`** (full-art), nonfoil.

**Frame/finish treatment classes present:**

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| full-art, no frame effect | 300 | all bands | `fa` | KEPT (collectible-alt) — every print surfaces via the treatment sub-selector |
| full-art, `legendary` frame effect | 36 | all bands (12 cards × 3) | `fa` | KEPT — same class, legendary crown only |
| full-art, `enchantment` frame effect | 27 | all bands (9 cards × 3) | `fa` | KEPT — same class, enchantment frame only |
| showcase / borderless / extended-art / etched | 0 | — | — | none present |

**v2/v3 scarcity versions (CN 122–363, 242 prints): kept (default) — pending owner review.** These are distinct-art, pack-scarce (~10% / ~5% of slots) versions of the v1 cards; nothing in the metadata separates them other than CN.

**`promo_types` dupe-foil / stamped signals:** none — `promo_types` is null on every print, there are no foils, so no dupe-foil candidate exists. Proposed `[dupe_foil] slz = []`.

**Full-art convention:** `full_art = TRUE` on all 363 prints.

**Missing-set consequence:** because every print is `fa` (not `regular`), the rare/mythic/uncommon-chase sub-selectors find nothing; the `treatment=preferred` sub-selector carries the whole set **including commons and uncommons** — an unconfigured→configured `missing-set slz` would list all 363 prints.

---

## 3. Chase variants

n/a in the `_modifier_chase` (uncommon-regular) sense — no `regular` prints exist. Note that the bare `chase` modifier matches **all 363** (each name has exactly 3 distinct-art `fa` prints), so `set:slz+related chase` is not a useful filter here. The real "chase" axis is the v2/v3 version scarcity (§1).

---

## 4. Scenes / posters / panoramas

None. No borderless/inverted prints, no `poster` promo_type; versions are per-card alternates, not multi-card panoramas.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Candidate | Status | Rationale |
|---|---|---|
| v2 + v3 versions (CNs 122–363, pinned by `collector_numbers`) | kept (default) — pending owner review | Pack-scarcity tiers (~10% / ~5%) of distinct art; no promo_type/frame signal, so a rule would need the 242-CN list. Prices were all null at audit time, so `set_status.py` concentration check could not evaluate the $ shape. |

Before/after missing totals: n/a (family unconfigured; no prices on Scryfall as of 2026-11-01).

Filtered globally: none apply (no serialized, no digital/arena-stamped prints — `missing | grep -i arena` → 0).

---

## 6. PRM destinations

n/a — no promo/prerelease channel; the product is the Secret Lair-subtype booster itself.

---

## 7. Edge cases & gotchas

- **Prices unpopulated.** At audit time Scryfall had `usd` null on effectively the whole set (one uncommon at $0.25), so value / EV / missing-$ reports read ~$0 until the market fills in. Re-sync (`mm set sync slz`) later.
- **Not a `sld` drop.** Although MTGJSON tags the pack `subtype: secret_lair`, Scryfall files it as its own `box` set `slz`, not under `sld`; the Secret Lair tools (`sld.recent_drops`, `secret-lair-value`) key on `sld` and won't see it.
- **Rarity ≠ scarcity.** A v3 common (weight 1) is far rarer than a v1 rare in pack terms; rarity filters (`rarity=rare`) don't express version scarcity — use CN bands.
- **Name collisions:** each name appears exactly 3 times (CN N, N+121, N+242), all same rarity; no cross-set siblings in-family.
- Artist field is the brand `MSCHF` on every print (no per-card artist credit).

---

## 8. Code refs

None configured yet (proposals pending owner review).

- `config/families.toml` `[dupe_foil]` — no `slz` entry (proposal: `slz = []`).
- `config/families.toml` `[[unobtainable.slz.rules]]` — none (v2/v3 scarcity rule pending owner review).
- Scenes — none.

---

## 9. Product types

| Product | Archetype (→ [product-types.md](../product-types.md)) | Family-specific detail |
|---|---|---|
| Secret Lair x MSCHF - The Zeta Set Booster Pack | Secret Lair (booster-pack subtype) | `contents.pack = [{code: default, set: slz}]`; no decklist; randomized, so value via booster EV, not deck value |

**Booster types (for `sealed-value` EV).**

| Booster type | Notes (what MTGJSON can't say) |
|---|---|
| `default` | 7 cards: 3 common + 2 uncommon + 1 rare/mythic + 1 wildcard (any of the 363). Version weights 17:2:1 (v1:v2:v3) per rarity sheet; rare/mythic sheet weights 51/6/3 rare, 34/4/2 mythic. `sealed_value.py slz --list-boosters` → EV $0.00 at **0.1% coverage** (prices null, not an unsynced-set problem). |
