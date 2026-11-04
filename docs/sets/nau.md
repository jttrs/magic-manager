# `nau` — `Nauctis: The Sunken Realm`

> Per-family memory doc. Read this before answering set-specific questions about
> `nau` or working on `nau`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `nau`
**Family root type:** `expansion`
**Family released:** 2027-02-05 (**UNRELEASED** at audit time — pre-release placeholder in Scryfall/MTGJSON)
**Last audit:** 2026-11-01 via `/characterize-set nau` (batch, non-interactive).

> ⚠️ **Placeholder family — re-characterize after spoilers/release.** At audit time
> Scryfall lists `nau` with `card_count: 0` (no cards spoiled) and one token-set
> card; MTGJSON's `NAU` has `totalSetSize: 0`, 1 token, no decks, no booster data.
> Every section below is "n/a — no cards yet" except the token. Re-run
> `/characterize-set nau` once the set is spoiled (expect a full premier-expansion
> family: commander/promo/art-series/masterpiece siblings may appear then).

---

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `nau` | expansion | 0 | 2027-02-05 | parent — `parent_set_code: null`, no cards spoiled yet |
| `tnau` | token | 1 | 2027-02-05 | child (`parent_set_code: nau`) — only card is `God Pack Celebration Card` |

**Separately-rooted bonus sheets:** none found. Scryfall `/sets` scan of
2026-10-01 → 2027-03-01 shows only `pw27`/`pf27` (yearly promo sets, not
family-specific) and the unrelated `trk`/`fra`/`mbc` families (plus `tfdc`, an `fdc` token child) in the window.

No `--only` needed.

---

## 2. Treatments

Survey (`survey_treatment_signature.py NAU`, 2026-11-01): 1 print total in the family.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 1 | `tnau` 10 | `regular` (foil-only) | the lone print is a **token** (`is_token=1`) → hard-excluded from missing-set by `missing.missing_printings` |

- No showcase, borderless, extended-art, etched, or fancy-foil classes exist yet.
- `promo_types`: none present. No dupe-foil / stamped signals to evaluate.
- **Full-art convention:** n/a (no cards).

---

## 3. Chase variants

n/a — no cards spoiled.

---

## 4. Scenes / posters / panoramas

n/a — no cards spoiled.

---

## 5. Unobtainable rules

None. No alt-treatment tiers exist yet, so no keep/exclude decisions are
pending. `set_status.py nau` reports 0 owned, missing "not configured" — no
concentration note (nothing priced).

---

## 6. PRM destinations

n/a — no promo sibling (`pnau`) exists yet. Expect a `pnau` prerelease/promo
set and WPN prints under `pw27` once spoiled; record CN patterns then.

---

## 7. Edge cases & gotchas

- **`God Pack Celebration Card`** (`tnau` 10): `layout: token`, `type_line: Card`,
  no oracle text, foil-only, black border, 2015 frame, no price. A pack-insert
  "celebration" card (presumably marks a god-pack opening), filed as a token —
  tracked if owned, never in missing-set buy lists. Scryfall's `tnau` CN 10 with
  no CNs 1–9 suggests the real token list hasn't been published yet.
- `mm query missing-set nau` currently fails with the "requires per-family
  dupe-foil config" `SelectorParseError` (family unconfigured); `mm query show
  'set:nau+related missing'` lists only the token.
- Arena leak check: n/a (no cards).

---

## 8. Code refs

- `config/families.toml` — None configured yet (proposals pending owner review).
  Once spoiled, the family will need at least a `[dupe_foil]` entry (possibly
  empty) for `missing-set` to run.

---

## 9. Product types

n/a yet — MTGJSON has no `sealedProduct`, no decks, and no booster data for
`NAU` (`sealed_value.py nau --list-boosters` → "no booster data in MTGJSON").
Fill in Play/Collector booster types, Bundle, and any Commander/Jumpstart
products after release. Archetype definitions: [`../product-types.md`](../product-types.md).

| Booster type | Notes |
|---|---|
| — | none in MTGJSON as of 2026-11-01 |
