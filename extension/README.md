# magic-manager companion (Chrome extension)

Reads your Mana Pool, TCGplayer or Card Kingdom cart, your open store tabs (Deals), watched store pages, store order history, Moxfield and Archidekt decks and your Moxfield collection / binders in **your own browser**.
Each time, it shows you exactly what it would send and waits for you to press Send. Plain
JavaScript, no dependencies, no build step: what you see here is what runs.

- Install, pair and use: [`docs/browser-companion.md`](../docs/browser-companion.md)
- What it can and can't do, and why: [`docs/browser-companion-security.md`](../docs/browser-companion-security.md)
- A site changed and a read broke: `.claude/skills/scrape-doctor/SKILL.md`
- Chrome Web Store listing, privacy policy and release: `store/listing.md`,
  [`docs/privacy-companion.md`](../docs/privacy-companion.md),
  [`docs/browser-companion.md` § Chrome Web Store](../docs/browser-companion.md#chrome-web-store)

`src/stores.js`, `src/tokens.css`, `icons/*.png` and the manifest's permission and icon lists are generated from `config/vendors.toml` by
`uv run python scripts/build_extension.py`. Don't edit them by hand.
