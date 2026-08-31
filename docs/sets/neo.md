# `neo` — Kamigawa: Neon Dynasty

> Per-family memory doc. Read this before answering set-specific questions about
> `neo` or working on `neo`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `neo`
**Family root type:** `expansion`
**Family released:** 2022-02-18 (Kamigawa: Neon Dynasty — a cyberpunk-Kamigawa Standard set; PRE-fancy-foil era)
**Last audit:** 2026-08-30 via `/characterize-set neo` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `neo` | expansion | 517 | parent |
| `nec` | commander | 179 | Neon Dynasty Commander (2 precon decks) |
| `pneo` | promo | 148 | promos — 69 `promopack`+`stamped` (`Np`) + 77 `prerelease`+`datestamped` (`Ns`) + 2 `resale` ★ |
| `aneo` | memorabilia | 81 | Art Series (not in default checklist) |
| `yneo` | alchemy | 30 | Alchemy digital-only (globally filtered) |
| `mneo` | minigame | 3 | Minigame cards |
| `sneo` | token | 9 | Substitute cards |
| `tneo` | token | 19 | tokens |
| `tnec` | token | 12 | commander tokens |

Default `set:neo+related` resolution works; `neo` is the true parent (all others
root to it). **Sync gotcha:** a bare `master-list neo` syncs only `neo`/`nec`;
`pneo`/`aneo`/`yneo`/tokens are 0-local until `mm set sync neo --include-related`.
The 69 `pneo` `promopack`+`stamped` promos are invisible until then (the
SNC/ECL/SOS/BLB/FDN/MAT trap — the initial audit undercounted 293→304 prints
until the full family synced).

---

## 2. Treatments

**No same-art dupe-foil signal** — `FAMILY_DUPE_FOIL_PROMO_TYPES["neo"] = frozenset()`
(like TLA/SPM/SOS/MAT). NEO is a 2022 set that predates the manafoil/halofoil/
fracturefoil "same-art fancy-foil sheet" era; its premium treatments are all
distinct-art, so nothing goes in DUPE_FOIL. The chase tiers are excluded via §5.

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `neonink` | `b\|shw\|ff` | **no — distinct-art chase, excluded (§5)** | 4 prints, Hidetsugu, Devouring Chaos ONLY (`neo` 429-432), foil-only, ~$35-$514. Four NEON COLORWAYS, each its own `illustration_id` (verified 429/430/431 all differ from the boosterfun showcase 378) — NOT a dupe. Analog of TLA's neonink. Excluded via §5. |
| `thick` | `b\|ff` | **no — display product, excluded (§5)** | 2 prints, `nec` oversized "thick stock" display commanders (Chishiro 77, Kotori 78). No plain-showcase sibling (only base + extended), so DUPE_FOIL wouldn't pair them anyway. Excluded via §5. |
| `boosterfun` | `b` / `b\|shw` / `ext` | **no — distinct alt-art** | 240 prints. Showcase (ninja/soulscar frames), borderless, extended-art alt-arts — KEPT. |
| `concept` / `setextension` / `stepandcompleat` | `b` | **no — distinct alt-art** | Jin-Gitaxias, Progress Tyrant (`neo` 513/514) — the Phyrexian-language "concept praetor" alt-arts. Distinct art, KEPT. |
| `promopack` (alone) | `b` | **no — distinct alt-art** | 5 prints (`neo` 508-512: Enthusiastic Mechanaut, Jukai Naturalist, Secluded Courtyard, Silver-Fur Master, Spirited Companion). In-set promo-pack alt-arts, NO `stamped` — KEPT (the §5 rule keys on `stamped`, sparing these). |
| `promopack` + `stamped` | (stamp) | n/a — scarcity | 69 `pneo` `Np` prints. Same card as a kept `neo` base sibling + a stamp. Excluded via §5 `{stamped}` rule. |
| `prerelease` + `datestamped` | (stamp) | n/a — scarcity | 77 `pneo` `Ns` prints. Auto-dropped by the Step-2 datestamped filter. |
| `resale` | (promo) | **no — distinct** | 2 `pneo` ★ prints (Goro-Goro 145★, Raiyuu 232★). Distinct art, kept. |
| `rebalanced` / `alchemy` | (digital) | n/a | 17 A-prefixed `neo` prints + `yneo`. Digital-only, globally filtered. |

**Full-art convention:** boosterfun showcase (ninja / soulscar / ukiyo-e frames).

---

## 3. Chase variants

No uncommon multi-variant chase surfaced. The premium tiers are the neonink
Hidetsugu colorways (§5) + the ukiyo-e legendary-dragon cycle (`neo` 406-411) and
channel lands (`neo` 412-416) — distinct boosterfun alt-arts, KEPT. **No
serialized tier** in this pre-serialization-era family.

---

## 4. Scenes / posters / panoramas

**None.** The `neo` 406-416 borderless run (ukiyo-e dragons + channel lands) is a
themed cycle but each card is by a DIFFERENT Japanese artist (Ishikawa Kenta,
Yukihiro Maruo, Yoshiya, …) — not a contiguous single-artist panorama. Fails the
scene definition (contiguous CN + same artist). No `FAMILY_SCENES["neo"]`.

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["neo"]` = two rules — `{neonink, thick}` + `{stamped}`
(both added 2026-08-30).

**`{neonink, thick}`** — chase-tier premiums the user doesn't shop for.
`neonink` = the 4 Hidetsugu neon colorways (`neo` 429-432, foil-only, up to
~$514) — distinct art, so the dupe filter would keep them; this rule removes them.
`thick` = the 2 `nec` oversized display commanders. `any_of` (they never
co-occur) catches exactly these 6 prints; every card's base/showcase/extended
prints stay in scope.

**`{stamped}`** — 69 `pneo` `promopack`+`stamped` promo-pack scarcity variants.
Validated: all 69 have a non-stamped `neo` base sibling (2p→2, 134p→134, …), and
the 5 `promopack`-ONLY in-set alt-arts (`neo` 508-512, no `stamped`) are KEPT —
signal is `stamped` ONLY (SNC/EOE/ECL/BLB/FDN lesson).

**No serialized/headliner rule** — no such tier in this family.

**Missing-set impact:** the two rules drop the family to **304 prints / $821** at
0 owned (the `{stamped}` rule alone removes ~80 promo prints: 373→293 before the
full-family resync bumped the base count). Top prints are legit channel lands
(Boseiju ~$63/$50, Otawara ~$40) + The Wandering Emperor + the Jin-Gitaxias
concept praetor — no scarcity artifact.

Globally filtered (not via a rule): `rebalanced`/`alchemy` (digital); the `Ns`
prerelease+datestamped promos (Step-2 filter).

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel |
|---|---|---|
| `Np` (e.g. `2p`, `134p`) | `pneo` | Promo pack — 69 `promopack`+`stamped` (excluded via §5) |
| `Ns` (e.g. `2s`, `88s`) | `pneo` | Prerelease datestamped — 77 `prerelease`+`datestamped` (auto-dropped, §2) |
| `N★` (145★, 232★) | `pneo` | Resale promo — 2 prints (Goro-Goro, Raiyuu), distinct art, kept |
| Promo-pack alt-art, `neo` 508-512 | `neo` (in-set, `promopack`-only) | Promo-pack alt-art (NOT `pneo`); KEPT in missing-set |

Resolve a PRM-stamped NEO card by name + the `p`/`s`/★ CN suffix per
`.claude/skills/bulk-add/SKILL.md`.

---

## 7. Edge cases & gotchas

- **neonink is distinct-art, NOT a dupe** — the 4 Hidetsugu prints are 4 neon
  colorways (distinct illustration_ids), so DUPE_FOIL wouldn't catch them (no
  same-art sibling) and shouldn't try. It's an UNOBTAINABLE chase like TLA
  neonink. Contrast the modern manafoil/halofoil "same-art fancy sheet" dupes.
- **`promopack` alt-art trap (508-512)** — in-set `promopack`-only alt-arts with
  NO `stamped`; the §5 `{stamped}` rule correctly spares them. (Same trap as
  ECL 402-406 / EOE 393-397 / SNC 463-467 / BLB 381-385 / SOS 363-367.)
- **`pneo` hidden until full sync** — 0-local after a bare master-list; the 69
  promo-pack stamps only appear after `--include-related`. The audit's first
  missing-set pass (before the pneo sync) undercounted and would have shipped a
  config that leaked all 69 — caught by re-validating after the full sync.
- **Jin-Gitaxias concept praetor (513/514)** — `concept`+`setextension`
  (+`stepandcompleat` on 514) Phyrexian-language alt-arts. Distinct art, KEPT.
- **`nec` is a genuine `set_type: commander`.** No topology gotcha.
- **Alchemy** (`yneo` + 17 A-prefixed `neo` prints) — digital-only, globally
  filtered. No arena-stamped leak (validated).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["neo"]` = `frozenset()`
  — **configured 2026-08-30.** No same-art dupe-foil signal (pre-fancy-foil-era
  set); empty set unblocks the `preferred` filter. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["neo"]` = two rules —
  `{"promo_types_any_of": {"neonink", "thick"}}` (4 Hidetsugu neon chases + 2
  thick display commanders) and `{"promo_types_any_of": {"stamped"}}` (69 `pneo`
  promo-pack stamps; `stamped` not `promopack`, sparing `neo` 508-512). §5.
- No `FAMILY_SCENES["neo"]` (themed cycle, mixed artists — §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| Neon Dynasty Commander (2 decks) | Commander deck | `nec` (179 cards). Import via `import-precon`; `source_set_code` → `neo`. |
| neon-ink Hidetsugu | (chase premium) | `neo` 429-432, foil-only, 4 colorways; excluded via §5. |
| thick-stock display commanders | (display product) | `nec` 77/78 oversized; excluded via §5. |
| Neon Dynasty Art Series | Art Series | `aneo` (81 cards, memorabilia). Not in default checklist. |
| Promo Pack | promo (`promopack`+`stamped`) | `pneo` `Np` — 69-card scarcity tier excluded via §5. |
