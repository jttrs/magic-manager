# `nau` — `Nauctis: The Sunken Realm`

> Per-family memory doc. Read this before answering set-specific questions about
> `nau` or working on `nau`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `nau`
**Family root type:** `expansion`
**Family released:** 2027-02-05 (**UNRELEASED** at audit time — pre-release placeholder in Scryfall/MTGJSON)
**Last audit:** 2026-11-27 (preview refresh of the 2026-11-01 placeholder audit).

> ⚠️ **Preview-season snapshot.** Scryfall now lists **24 `nau` printings** (9 card
> names), **4 `nac`** and **1 `tnau`**: early previews, not the set. Previewed cards
> carry no `frame_effects` or `promo_types` yet, so every print computes `regular`
> and the alternate-art CNs can't be classified. MTGJSON has the product list but
> no decks and no booster data. Re-run `/characterize-set nau` after release
> (expected 2027-02-05), then add the family's `[dupe_foil]` entry.

---

## 1. Family map

| Code | `set_type` | Cards (Scryfall, 2026-11-27) | Released | Notes |
|---|---|---:|---|---|
| `nau` | expansion | 24 | 2027-02-05 | parent (`parent_set_code: null`); 9 previewed names, CNs 5–410 |
| `nac` | commander | 4 | 2027-02-05 | **new since the first audit**: Nauctis Commander — face commanders "The Ignoble Serpent" 6 and "Zekes, Acid Rock Fan" 8 (foil-only), Crucible of Worlds 345 / 365 |
| `tnau` | token | 1 | 2027-02-05 | only card is `God Pack Celebration Card` 10 |

No `pnau` promo set or art series yet. `set:nau+related` covers all three codes.

---

## 2. Treatments

Survey (`survey_treatment_signature.py NAU`, 2026-11-27): every print computes `regular`
(26 nonfoil rows, 29 foil rows), because preview data has no frame or promo tags yet.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base previews | 9 | `nau` 5, 70, 121, 220, 234, 238, 260 + repeats | `regular` | rarity sub-selectors |
| alternate CNs of the same names | 15 | `nau` 281–410 (e.g. Salinae, the Ocean Mother 70 / 321 / 353 / 369 / 409) | `regular` for now | **unclassified**: mostly distinct art (Salinae 321, 353, 409 differ from 70), but 353 and 369 share art, so a fancy-foil or treatment-twin sheet is likely |
| commander face cards | 2 | `nac` 6, 8 (foil-only, legendary) | `regular` | mythic-regular |
| Crucible of Worlds | 2 | `nac` 345, 365 | `regular` | mythic-regular; two CNs, likely two frames |
| celebration token | 1 | `tnau` 10 | `regular` (foil-only) | token: hard-excluded from missing-set |

**Prices so far:** Abyssal Lotus 316 ~$100, Ring of Unity 317 ~$70 / 238 ~$47,
Calmwater Mentor 281 ~$60, Tecton, Malignant Ruin 121 ~$28, Goramou 311 ~$25.
Most prints are unpriced.

---

## 3. Chase variants

Too early to tell. The 281–410 alternate CNs are where chase tiers will show once
Scryfall tags their frames.

---

## 4. Scenes / posters / panoramas

None detected yet.

---

## 5. Unobtainable rules

None. No treatment tiers can be told apart yet, so no keep/exclude decisions are
pending. The family still has no `[dupe_foil]` entry, so `mm query missing-set nau`
refuses.

---

## 6. PRM destinations

No `pnau` set yet. Expect a prerelease / promo set and WPN prints under `pw27`.

---

## 7. Edge cases & gotchas

- **`God Pack Celebration Card`** (`tnau` 10): `layout: token`, `type_line: Card`,
  foil-only, no price. A pack-insert celebration card, filed as a token, so it's
  tracked if owned but never in missing-set lists. Still no `tnau` 1–9.
- **Commander face cards are quoted names** (`"The Ignoble Serpent"`,
  `"Zekes, Acid Rock Fan"` include the quote marks on Scryfall); search by the
  quoted name.
- **Same art on two CNs:** Salinae 353 and 369 share `illustration_id`. Once tags
  arrive, check whether one is a fancy-foil twin for `[dupe_foil]`.

---

## 8. Code refs

- `config/families.toml` — None configured yet (proposals pending owner review).
  Once spoiled, the family will need at least a `[dupe_foil]` entry (possibly
  empty) for `missing-set` to run.

---

## 9. Product types

Archetype definitions: [`../product-types.md`](../product-types.md). MTGJSON lists the
products but no decks or booster data yet (`sealed_value.py nau --list-boosters` →
"no booster data in MTGJSON").

| Product | Archetype | Family-specific detail |
|---|---|---|
| Booster Pack / Booster Box | booster product | a single "Booster Pack" (no separate Play/Draft naming), plus a **Box Topper Pack** |
| Collector Booster Pack / Box | booster product | — |
| Bundle | Bundle | — |
| Draft Night | limited aid | — |
| Commander Decks ×4 | Commander deck | Blood in the Water, Merfolk Regiment, Seal the Deal, Terrors of the Abyss, each also as a **Premium Edition** (`nac`) |
