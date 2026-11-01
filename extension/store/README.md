# Store kit — magic-manager companion

Everything needed to list the companion on a browser store. Kept beside the extension but **never
shipped in the zip** (`companion.EXCLUDE_DIRS`).

| File | What it is |
| --- | --- |
| `listing.md` | Listing copy, single purpose, per-permission justifications, data-use answers, reviewer test instructions (written for the Chrome Web Store dashboard; Edge reuses it — see below). |
| `store.toml` | The published store pages the app's setup dialog links to: `[chrome_web_store]` and the optional `[edge_add_ons]`. Empty = not listed. |
| `screenshots/*.png` (1280×800), `promo-small.png` (440×280) | Captured from the real extension pages by `uv run python scripts/capture_store_assets.py`. |
| `edge-logo-300.png` | Edge Add-ons' store logo, generated from the favicon shapes with the icons (`scripts/build_extension.py`; `--check` keeps it current). |

**The package** is the same for both stores: the `--store-zip` (manifest at the zip root) that
`uv run python scripts/build_extension.py --store-zip <file>` builds and the `extension-release`
workflow attaches to every `companion-v*` GitHub release as `magic-manager-companion-<version>-store.zip`.

Chrome Web Store release steps: [`docs/browser-companion.md` § Chrome Web Store](../../docs/browser-companion.md#chrome-web-store).

## Microsoft Edge Add-ons (optional)

Edge is Chromium: the companion's Manifest V3 runs **unchanged** — same zip, same APIs
(`scripting`, `storage`, optional host permissions, `chrome.*` namespace), and `minimum_chrome_version`
is honored (Edge versions track Chromium's). Nothing in the shipped extension names a store: no
`update_url`, no `key`, no Chrome Web Store link (a test, `test_shipped_extension_names_no_single_store`,
keeps it that way), so each store serves its own updates.

Differences worth knowing:

- **A new extension id.** An Edge Add-ons install gets its own id, like a Chrome Web Store install —
  pair it with the app again; the app answers whichever companion is paired with its address.
- **Wording.** Some messages say "Chrome" or `chrome://extensions`; in Edge, `chrome://extensions`
  opens `edge://extensions`, and the steps are the same. No change needed for review.
- **The Deals "open tabs on this Mac" fallback** (AppleScript, `tabs.py`) reads Google Chrome or Safari, not Edge; in Edge the
  companion reads the tabs itself, which is the normal path.

### Owner's steps (one-time)

1. **Register** in [Partner Center](https://partner.microsoft.com/dashboard/microsoftedge/overview) for the
   Microsoft Edge program — **free** (a Microsoft account or GitHub sign-in; individual account).
2. **Create new extension** → upload the latest `magic-manager-companion-<version>-store.zip` from the
   GitHub release (or build it: `uv run python scripts/build_extension.py --store-zip companion-store.zip`).
   Wait for the package check.
3. **Availability:** visibility **Hidden** (installable from the link, not searchable — the Edge
   equivalent of Chrome's *Unlisted*); markets: all.
4. **Properties:** category *Productivity*; privacy policy URL
   `https://github.com/jttrs/magic-manager/blob/main/docs/privacy-companion.md`; website
   `https://github.com/jttrs/magic-manager/tree/main/extension`; mature content: no.
5. **Store listing (English):** description from `listing.md` → *Description*; extension logo
   `edge-logo-300.png`; small promotional tile `promo-small.png`; screenshots `screenshots/*.png`.
6. **Submit** — paste `listing.md` → *Test instructions* into *Notes for certification*. Review
   takes up to about a week.
7. **After approval:** copy the listing's address (`https://microsoftedge.microsoft.com/addons/detail/…`)
   into `[edge_add_ons] url` in `store.toml` (and the Product ID from the Overview page into
   `product_id`), in a PR. Until then — or on a host ahead of the repo — set
   `MM_COMPANION_EDGE_STORE_URL`. The setup dialog then shows **Add to Edge** (beside *Add to Chrome*
   when both exist). Nothing in the app changes while it's empty.

**Updates:** for each release, open the extension in Partner Center → *Packages* → upload the new
`-store.zip` (its version must be higher) → *Publish*. The release workflow uploads only to the
Chrome Web Store; Edge uploads stay manual.
