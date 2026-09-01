# `msh` — Marvel Super Heroes

> Per-family memory doc. Read this before answering set-specific questions about
> `msh` or working on `msh`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `msh`
**Family root type:** `expansion`
**Family released:** 2026-06-26 (Marvel Super Heroes — a Universes Beyond
Commander-focused Marvel set)
**Last audit:** 2026-08-31 via `/characterize-set msh` (steps 1-9).

---

## 1. Family map

| Code | `set_type` | Cards (EN synced) | Notes |
|---|---|---:|---|
| `msh` | expansion | 453 | parent |
| `msc` | commander | 866 | Marvel Super Heroes Commander (4 decks + Collector's Edition twins) |
| `fmsc` | memorabilia | 61 | Commander Jumpstart Front cards |
| `amsh` | memorabilia | 66 | Art Series (not in default checklist) |
| `tmsc` | token | 32 | commander tokens |
| `tmsh` | token | 27 | tokens |

Default `set:msh+related` resolution works; `msh` is the true parent. **No promo
code** (`pmsh` doesn't exist) — msh has no prerelease/promo-pack tier. **Sync
gotcha:** `fmsc`/`tmsc`/`amsh`/`tmsh` are 0-local after a bare `master-list msh`;
run `mm set sync msh --include-related` for the full 1,505-card family. The audit
was done on complete data after this sync.

**Not related to `mar` or `spm`.** Three separate Marvel products, each its own
Scryfall-null-parent root: `msh` (this, Marvel Super Heroes, 2026-06), `spm`
(Marvel's Spider-Man, 2025-09), `mar` (Marvel Universe masterpiece sheet, ships
with spm). Do NOT conflate — only `mar` is grouped under `spm` (via set_targets);
`msh` stands alone.

---

## 2. Treatments

**No dupe-foil signal retained** — `FAMILY_DUPE_FOIL_PROMO_TYPES["msh"] = frozenset()`.
`surgefoil` is the family's fancy foil but is excluded WHOLESALE via §5 (not
DUPE_FOIL) because of a frame-code mismatch (see below).

| promo_type / treatment | Keyword | Dupe? | Notes |
|---|---|---|---|
| `surgefoil` | `ff` (297) / `b\|ff` (7) / `fa\|ff` (10) | **yes — excluded via §5** | 335 prints (+`universesbeyond`), the commander-deck collector-foil treatment. Same art as a non-foil sibling (verified Abomination MSC 47 shares `illustration_id 203990c4` with MSC 355). Near-zero foil value. Excluded wholesale (§5). |
| `universesbeyond` | (base) | n/a | 1,439 prints — carried by every card (UB product constant), not a treatment signal. |
| `poster` | (empty→regular) | **no — distinct art, KEPT** | 3 prints: Captain America (msh 387, ~$65), Namor (391, ~$49), Doctor Doom (394, ~$140). Distinct poster art; KEPT in missing-set. |
| `headliner` + `cosmicfoil` | `ff` | n/a — chase, excluded (§5) | 1 print: The Mind Stone msh 385, the set's headline ultra-rare. §5. |
| borderless character foils | `b` | **no — distinct art, KEPT** | The msh 386-401 borderless-inverted character foils (Thanos 400 ~$160, Ultron 401, etc.) — distinct art, KEPT. **Exception:** The Mind Stone 386 (~$1,699) is excluded as a chase (§5). |

**Full-art convention:** borderless-inverted showcase (UB Marvel character art).

**Why surgefoil is §5, not DUPE_FOIL:** the surgefoil prints compute to bare `ff`
(plain frame), but their same-art non-foil siblings compute to `ext` (extended-art
frame). The dupe-foil Step-3 matches on `(name, codes-minus-ff)` — `{}` (surgefoil)
vs `{ext}` (sibling) never align, so DUPE_FOIL leaks ~264 of them. Same class of
frame-mismatch as MAT halofoil / NEO. A wholesale `{surgefoil}` exclusion is exact.

---

## 3. Chase variants

No uncommon multi-variant chase. The premium tiers are: the headline Mind Stone
385 (headliner+cosmicfoil) + its $1,699 borderless foil 386 (both §5), and the
borderless character foils (kept). No serialized tier.

---

## 4. Scenes / posters / panoramas

**None configured.** The borderless-inverted ranges DO have long single-artist
runs (msh: Annie Wu 314-319, Leinil Francis Yu 320-323, Kev Walker 324-327, Johan
Grenier 334-351; msc: Thanh Tuấn 501-506, Kieran Yanner 507-512), but these are
individual character showcase cards by one artist, NOT a single contiguous
multi-card panorama artwork (the `FAMILY_SCENES` / scene_table concept). No
`FAMILY_SCENES["msh"]`. (Re-evaluate if any run is confirmed to be one connected
artwork.)

---

## 5. Unobtainable rules

`FAMILY_UNOBTAINABLE_RULES["msh"]` = three rules — `{headliner}` + `{surgefoil}`
+ a CN-pinned Mind Stone 386 rule (all added 2026-08-31).

**`{headliner}`** — MSH 385 The Mind Stone (`headliner`+`cosmicfoil`), the set's
headline ultra-rare. Exactly 1 print carries `headliner`. Analog of TLA Aang / EOE
Sothera / ECL Bitterbloom Bearer.

**`{surgefoil}`** — all 335 surgefoil collector foils (§2). The user doesn't chase
the collector-foil treatment; excluded wholesale (264 dupe a non-foil sibling, 71
are foil-only staples like Arcane Signet / Command Tower — user opted to drop ALL).

**Mind Stone 386 (CN-pinned)** — `{"collector_numbers": {"386"}, "border_color":
"borderless"}`. The ~$1,699 borderless-foil Mind Stone, the set's flagship $ chase.
Distinct art (not the headliner 385), no distinguishing promo_type, so pinned by CN
+ border_color. The base (msh 21) and other prints stay in scope. **This is the
first use of the `collector_numbers` rule condition** (added to the rule engine
this session for exactly this case).

**No `{stamped}` rule** — `stamped` does not occur in this family (0 prints); no
promo-pack scarcity tier. The `poster` cards (387/391/394) are distinct art, KEPT.

**Missing-set impact:** the rules drop the family from **453 → 232 prints
($4,011 → $2,087)** at current ownership — surgefoil tier (~$81) + Mind Stone 386
(~$1,699) + headliner removed. Top remaining prints are legit borderless character
foils (Thanos ~$160, Doctor Doom poster ~$140) — no scarcity artifact.

Globally filtered (not via a rule): none unusual (no arena/rebalanced/serialized in
the family — validated 0 arena-stamped).

---

## 6. PRM destinations

**No promo code in this family** (`pmsh` doesn't exist) — msh has no prerelease
datestamped or promo-pack channel, so there's no PRM-stamp resolution to record.
Art Series lives in `amsh` (not in the default checklist).

---

## 7. Edge cases & gotchas

- **surgefoil frame-mismatch** — the reason surgefoil is a §5 wholesale rule, not
  DUPE_FOIL: surgefoil computes to bare `ff` while its same-art sibling is `ext`,
  so the codes-minus-ff sibling match fails. When a fancy-foil's non-foil twin is
  the *extended-art* print (not a plain print), DUPE_FOIL can't pair them — reach
  for a `promo_types_any_of` wholesale exclusion. (Same lesson as MAT halofoil.)
- **Mind Stone has 3 prints** — base (21, kept), headliner+cosmicfoil (385,
  §5-excluded), borderless foil (386, §5-excluded by CN). Only the base stays in
  missing-set.
- **`collector_numbers` rule condition is new** — added to
  `_matches_unobtainable_rule` this session to pin msh 386 (a chase with no
  distinguishing promo_type). Pair it with `border_color`/`frame_effects` for
  safety so it can't accidentally match a reprint of the same CN in another code.
- **Three distinct Marvel products** — msh ≠ mar ≠ spm. Only mar is folded under
  spm (set_targets); msh is standalone. `stamped`=0 here (unlike no other recent
  set's promo tier).
- **No digital tier** — 0 arena/rebalanced/alchemy in the family (validated).

---

## 8. Code refs

- `selectors.py:FAMILY_DUPE_FOIL_PROMO_TYPES["msh"]` = `frozenset()`
  — **configured 2026-08-31.** No dupe-foil signal (surgefoil frame-mismatch →
  wholesale §5 exclusion); empty set unblocks the `preferred` filter. §2.
- `selectors.py:FAMILY_UNOBTAINABLE_RULES["msh"]` = three rules —
  `{"promo_types_any_of": {"headliner"}}` (Mind Stone 385 headline chase),
  `{"promo_types_any_of": {"surgefoil"}}` (335 collector foils), and
  `{"collector_numbers": {"386"}, "border_color": "borderless"}` (the $1,699
  borderless Mind Stone 386). §5.
- `selectors.py:_matches_unobtainable_rule` — gained the `collector_numbers`
  condition this session (first used by the msh 386 rule).
- No `FAMILY_SCENES["msh"]` (single-artist showcase runs, not panoramas — §4).

---

## 9. Product types

Archetype definitions live in [`../product-types.md`](../product-types.md).
Family-specific detail:

| Product | Archetype (→ product-types.md) | Family-specific detail |
|---|---|---|
| MSH Commander (4 decks) | Commander deck | `msc`. Avengers Assemble, Doom Prevails, The Fantastic Four, Wakanda Forever — each with a **Collector's Edition twin** (8 MTGJSON products total). Import via `import-precon`; `source_set_code` → `msh`. |
| Marvel Super Heroes Art Series | Art Series | `amsh` (66 cards, memorabilia). Not in default checklist. |
| surgefoil collector foils | (collector-booster foil) | 335 prints; excluded via §5. |
| The Mind Stone chases | (headline chase) | msh 385 (headliner+cosmicfoil) + 386 (borderless foil ~$1,699); both §5. |
