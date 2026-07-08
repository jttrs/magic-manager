# LTR borderless "scenes" — artist-run analysis

The LTR borderless-inverted print run (`b` treatment) groups into contiguous collector-number ranges by artist, each depicting a Lord of the Rings scene. Entirely Scryfall-native data — no manual annotation needed. LTR 433 (Orcish Bowmasters, Tyler Jacobson) sits inside the Jacobson Minas Tirith / Battle of the Pelennor scene, LTR 420–437.

## Inventory across the 7 detected scenes

### Livia Prima — 399–404 (6 cards, Shire/Hobbits)

- Own 0/6 in either finish. Complete NF: **$36.32**, foil: **$36.60**.

### Colin Boyer — 405–410 (6 cards, Balrog/Moria)

- NF: own 2 partials (LTR 406 ×1, LTR 408 ×2). Missing: 405, 407, 409, 410. Complete NF: **$10.84**, foil: **$19.52**.

### David Rapoza — 411–419 (9 cards, Isengard/Ents)

- Mostly NF, but 414 & 416 have foil copies mixed in. If you pick NF for this scene: missing 412, 413, 415 → **$12.95**. If you pick foil: missing all except 414, 416 → **$53.92** (foil 418 alone is $37).
- **Recommendation:** complete in NF — you already have foil for only 2 of 9 and the mythic 418 is prohibitive in foil.

### Tyler Jacobson — 420–437 (18 cards, Minas Tirith/Pelennor — this contains LTR 433)

- NF-only ownership except LTR 426 (2 foil). Missing 9 cards in NF: 420, 424, 430, 431, 433, 434, 435, 436, 437. Complete NF: **$80.05** (of which Orcish Bowmasters 433 = $56.07). Complete foil: **$138.23**.
- **Recommendation:** NF — the one foil (LTR 426 Oliphaunt) is $0.45 to buy in NF, the rest of the scene is uneconomical in foil.

### Martina Fačková — 438–441 (4 cards, Scouring of the Shire)

- Own NF 440, NF+foil 441. Complete NF: **$8.90** (missing 438, 439). Complete foil: **$10.32**.

### Kieran Yanner — 442–447 (6 cards, Grey Havens)

- Foil-heavy scene: own foil for 442–447 minus 445 (which you have in both). Missing: NF 446+447 = $4.56. **Foil already complete — $0.00 to buy!**
- **Recommendation:** foil, you're done.

### Marta Nael — 448–451 (4 cards, Mount Doom climax)

- Own 0/4. Complete NF: **$90.57**, foil: **$95.16**. The One Ring 451 dominates the cost ($89.48 NF).

## Insight

- **Grand totals:** complete every scene in NF = **$244.19**, foil = **$353.75**. But per-scene "cheaper finish" mixing (per what you already own) drops to roughly **NF everywhere except Yanner (foil-done) = ~$149**.
- Purchasing entire scenes in a single finish avoids mismatch when placed together. The scene-by-scene finish recommendation above is the cheapest per-scene path that respects that constraint.
- The full stack of 7 scenes only accounts for 53 of 66 borderless prints — the remaining 13 are (a) the 6 basics 340–345 with 6 different artists (1 card each, not a scene) and (b) the showcase legendary run 302–331 (all showcase `frame_effect`, not inverted, filtered separately). LTR 398 Trailblazer's Boots is a solo Alexander Gering buybox promo, not part of Livia Prima's Shire scene — correctly excluded.
- **Durable fix:** could add a `scene` selector modifier — same shape as `chase`, groups borderless-inverted prints by (artist, contiguous-CN-run) and returns rows in runs of ≥3. Then `mm query show 'set:ltr scene owned'` would give this table anywhere.
