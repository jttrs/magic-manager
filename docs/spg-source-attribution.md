# Special Guests (SPG) and Media Insert (PMEI) source attribution

How to map a Special Guests or Magazine Insert printing to its parent release. **Documented but not implemented as of V1.5.** This file captures the approach so future work can pick it up without rediscovering the audit. Both SPG and PMEI follow the same pattern — see the dedicated section near the end for PMEI specifics.

## The problem

Special Guests is a long-running set of ~165 cards (and growing) released alongside specific main expansions:

- [Goblin Sharpshooter (SPG) 136](https://scryfall.com/card/spg/136/goblin-sharpshooter) released with Lorwyn Eclipsed (ECL).
- [Bitterblossom (SPG) ...](https://scryfall.com/sets/spg) released with the same ECL batch.
- Earlier SPG batches were released with LCI, MKM, OTJ, MH3, BLB, DSK, FDN, DFT, TDM, EOE, etc.

A user cataloging "what came with Lorwyn Eclipsed" expects the SPG cards from that release window to show up. But Scryfall's set hierarchy doesn't model the link.

## What Scryfall does NOT model

- `parent_set_code` — SPG has none. It's a top-level masterpiece set.
- `block` / `block_code` — not populated on SPG cards.
- Any card-level field — no "source release" metadata anywhere on the card record.

## What's available: `released_at`

The only signal is the `released_at` date on each card. SPG cards released on the same date as a parent expansion are part of that release window. Verified mapping (sample audit, May 2026):

| `released_at` | Parent expansion | Set code | SPG cards |
|---|---|---|---|
| 2023-11-17 | The Lost Caverns of Ixalan | LCI | 24 |
| 2024-02-09 | Murders at Karlov Manor | MKM | 10 |
| 2024-04-19 | Outlaws of Thunder Junction | OTJ | 10 |
| 2024-06-14 | Modern Horizons 3 | MH3 | 15 |
| 2024-08-02 | Bloomburrow | BLB | 10 |
| 2024-09-27 | Duskmourn: House of Horror | DSK | 10 |
| 2024-11-15 | Foundations | FDN | 10 |
| 2025-02-14 | Aetherdrift | DFT | 20 |
| 2025-04-11 | Tarkir: Dragonstorm | TDM | 15 |
| 2025-08-01 | Edge of Eternities | EOE | 10 |
| **2026-01-23** | **Lorwyn Eclipsed** | **ECL** | **20** |
| 2026-04-24 | Avatar: The Last Airbender | TLA | 11 |

Each batch of SPG cards shares a `released_at` value that matches the corresponding parent expansion's `released_at`. Cross-reference is unambiguous on date alone.

## Implementation sketch

### Schema

Add one nullable column to `cards`:

```sql
ALTER TABLE cards ADD COLUMN release_group_code TEXT;
```

### Populate at sync time

In `magic_manager/sets.py:sync()`, after upserting cards:

```python
# Build the date → expansion map from /sets. Uses already-cached set
# metadata; no extra Scryfall calls needed.
date_to_expansion: dict[str, str] = {}
for s in scryfall.all_sets():
    if s["set_type"] == "expansion" and not s.get("parent_set_code"):
        date_to_expansion[s["released_at"]] = s["code"]

# For each card we just synced where parent_set_code is None and the set is
# itself parent-less (orphan masterpiece-style sets like SPG, MAR), look up
# the release group.
for c in synced_cards:
    if c["parent_set_code"] or c["set_type"] != "masterpiece":
        continue
    parent_code = date_to_expansion.get(c["released_at"])
    if parent_code:
        # update DB
        conn.execute(
            "UPDATE cards SET release_group_code = ? WHERE scryfall_id = ?",
            (parent_code, c["id"]),
        )
```

This runs once per sync. The lookup is O(1) per card.

### Selector grammar extension

Add `+spg` (or `+release-group`) modifier to set selectors:

```
set:ecl              # Lorwyn Eclipsed expansion only
set:ecl+related      # ECL family (parent + siblings)
set:ecl+spg          # ECL family + SPG cards from the ECL release window
set:ecl+related+spg  # all of the above
```

Implementation: `_materialize_set()` in `magic_manager/lists.py` checks for the `+spg` modifier; if present, expands the code list with `'spg'` AND attaches a filter to only count SPG cards where `release_group_code = anchor`.

### Master-list integration

`mm set master-list ecl` would have a corresponding flag to include SPG attribution:

```
mm set master-list "Lorwyn Eclipsed" --include-spg
```

This emits one combined intake doc covering ECL family + SPG cards from the ECL window.

## Why this is deferred

1. **SPG works fine standalone today.** It's its own family in our system; `mm set master-list spg` produces a complete catalog of all 165 cards across all release windows.
2. **The cross-reference is recoverable from `released_at` whenever we want it.** Adding the column is cheap when needed.
3. **User said "SPG can stay its own set."** No urgency.
4. **The selector-grammar extension is non-trivial.** Better to design it once we have a real use case.

## When to revisit

- User explicitly asks to combine "SPG + parent expansion" in a master list or buy-list export.
- A new "Special Guests"-style set ships and we need to model the same pattern (e.g. if WotC adds another standalone reprint sheet that releases alongside specific expansions).
- Existing master-list completion math leaves SPG out and the user notices.

## Other orphan sets to consider

When implementing, check the same approach for:
- **MAR (Marvel Universe)** — `set_type: masterpiece`, no parent. Released with SPM (Spider-Man) per the existing UB family doc, but tagged separately on Scryfall. Would benefit from the same release-group attribution.
- **OMB (Through the Omenpaths Bonus Sheet)** — child of MAR but conceptually tied to SPM.
- **PMEI (Magazine / Media Inserts)** — see §"PMEI media inserts" below.
- Future masterpiece-style standalone sets following the same pattern.

---

## PMEI media inserts (same pattern, deferred)

`pmei` is the long-running "Magazine Inserts" promo set. `set_type: promo`, no `parent_set_code`. It contains hundreds of cards going back to 1995, mixed across IPs (Magic originals, Final Fantasy, Avatar: TLA, etc.). Each card has:
- `released_at` — when this specific insert dropped, e.g. `2025-07-03` for Ultimecia.
- `promo_types: ['mediainsert', 'universesbeyond', 'ff{i..xv}']` — the per-IP tag identifies the source franchise.

Example: [Ultimecia, Temporal Threat (PMEI) 2025-11](https://scryfall.com/card/pmei/2025-11/ultimecia-temporal-threat) is an FFVIII-themed insert tied to the Final Fantasy release window.

PMEI is the **same problem class as SPG**: a multi-IP promo set with no `parent_set_code`, where attribution is recoverable only via `released_at` (and, for UB-themed inserts, the per-IP `promo_types` tag).

### Differences from SPG

- **Volume:** PMEI is much larger and older (1995–present). Most cards aren't UB and have no per-IP tag.
- **Per-IP tag is a free hint:** Unlike SPG (where you must look up `released_at`), PMEI's UB inserts already carry `promo_types: ['ffviii']` etc. So the FF-window subset can be filtered with `set:pmei promo:ffi or promo:ffii or ...` — no date math needed.
- **Most non-UB PMEI cards have no clear "release window."** A 2010 Chandra promo from a magazine doesn't belong to any modern expansion in the way an SPG card belongs to ECL.

### Decision for V1

**Defer.** Per user direction (2026-05-27): "defer, it can be handled like SPG." PMEI is excluded from the FF family resolver today; it's just its own set. When SPG attribution is implemented, extend the same approach to PMEI:
- For UB-themed PMEI cards, prefer the `promo_types: ff*` tag over `released_at` (it's a stronger signal).
- For Magic-original PMEI cards, leave `release_group_code` NULL — there's no meaningful parent expansion.
