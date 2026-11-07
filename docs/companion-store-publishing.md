# Publishing the companion to the browser stores — runbook

**Status (2026-11-05): paused.** Not submitted to any store. Paused until the rebrand lands, since the
name, icons, screenshots and listing copy will all change. Until then the app's setup dialog keeps
showing the developer (unpacked) install, which works.

This page is the owner's step-by-step checklist. The material it uses already lives in the repo, so it
points there instead of copying it:

| What | Where |
| --- | --- |
| Listing copy, single purpose, permission justifications, data-use answers, reviewer test steps | [`extension/store/listing.md`](../extension/store/listing.md) |
| Store icons, screenshots, promo tile, Edge logo; Edge steps | [`extension/store/`](../extension/store/) ([`README.md`](../extension/store/README.md)) |
| Published store addresses the app links to | [`extension/store/store.toml`](../extension/store/store.toml) |
| How the app uses the store URL; release workflow | [`browser-companion.md` § Chrome Web Store](browser-companion.md#chrome-web-store) |
| Privacy policy | [`privacy-companion.md`](privacy-companion.md) |

## 0. Before you start (after the rebrand)

Anything that carries the name or the look has to be redone first. Changing the **name** after the
item is published means another review, and the old name stays in the listing's history.

- [ ] Manifest `name` / `description` (the description is the store *Summary*, ≤ 132 characters).
- [ ] Icons: the favicon shapes in `web/public/favicon.svg` → `uv run python scripts/build_extension.py`
      (regenerates `extension/icons/*` and `extension/store/edge-logo-300.png`; `--check` must pass).
- [ ] Screenshots + promo tile: `uv run python scripts/capture_store_assets.py`.
- [ ] `listing.md`: name, description, single purpose, and every URL (homepage, support, privacy
      policy, source) if the repo is renamed or moved.
- [ ] `docs/privacy-companion.md`: the product name, and the URL it will be served from.
- [ ] Bump the version (`uv run python scripts/build_extension.py --bump patch`) in the same PR.
- [ ] Decide which Google account owns the item. It can't move to another account later without
      Google support's help.

The repo must stay **public**, or the reviewer can't open the privacy-policy and source links.

## 1. Build the package

```bash
uv run python scripts/build_extension.py --check
```

```bash
uv run python scripts/build_extension.py --store-zip companion-store.zip
```

The store zip has `manifest.json` at the root (the plain `--zip` nests it in a folder for *Load
unpacked*, and the store rejects that). Its build is reproducible, so the printed sha256 matches the one
the `extension-release` workflow attaches to a `companion-v<version>` GitHub release, and either file
works. **Don't commit the zip.** It isn't git-ignored; delete it after uploading.

## 2. Chrome Web Store (unlisted)

**Account (one-time):**
1. Go to <https://chrome.google.com/webstore/devconsole> → sign in → accept the developer agreement → pay
   the one-time **$5**.
2. **Account** page: set a publisher display name and a contact email, then **verify the email**.
   Publishing is blocked until it's verified.
3. If you're asked to declare trader vs non-trader (EU DSA): **non-trader**. It's a free hobby item.

**Item:**
1. **+ New item** → upload `companion-store.zip`. Note the 32-letter **item id** in the dashboard URL.
2. **Store listing:** fill it from `listing.md` § Store listing tab. Description = the fenced block;
   Category = Tools; Language = English (United States). Icon = `extension/icons/icon-128.png`.
   Screenshots = `extension/store/screenshots/*.png`; small promo tile =
   `extension/store/promo-small.png`. Homepage + support URLs as listed; Official URL empty.
3. **Privacy practices:** fill it from `listing.md` § Privacy practices tab.
   - Single purpose = the quoted paragraph.
   - One justification box per permission (`storage`, `scripting`, host permissions). For the host
     box, paste the Mana Pool row plus both optional-permission rows.
   - Remote code = **No**.
   - Data usage: tick **Website content**, **Web history**, **Financial and payment information**,
     nothing else. Tick all three certifications.
   - Privacy policy URL = the GitHub link to `docs/privacy-companion.md`.
4. **Distribution:** Visibility **Unlisted**, all regions, free.
5. **Test instructions** (if the dashboard has the field): `listing.md` § Test instructions.
6. **Submit for review.** It usually takes a few days, sometimes about two weeks. Since 0.5.x the
   manifest lists `https://*/*` as an *optional* host permission (the pool **Pair** draws one origin
   from). Expect the dashboard to warn about broad host permissions, and the review to take longer.
   The justification row in `listing.md` explains that only one origin is ever requested. A rejection email
   names the field. Fix the text in `listing.md` in a PR first, so the repo stays the source of truth.

**After approval: one PR** (code review + `pr_review.py` stamp — `store.toml` is not docs-only):
- `extension/store/store.toml` → `[chrome_web_store] url = "https://chromewebstore.google.com/detail/<slug>/<id>"`
  and `extension_id = "<id>"`. Only that prefix is accepted (`companion.store_url()`); anything else
  is silently ignored, so copy the address from the store page itself.
- Check it: `uv run mm serve`, then the companion setup dialog shows **Add to Chrome** first and the
  developer install folded underneath. `MM_COMPANION_STORE_URL` overrides the file on a host.
- A store install gets a **new extension id**: pair it with the app again and remove the unpacked copy.

**Optional: automatic draft uploads.** With these five repository secrets, the `extension-release`
workflow uploads each tagged release's store zip as a **draft** (Chrome Web Store API v2). It never
publishes; you still press *Submit* in the dashboard.

| Secret | Where it comes from |
| --- | --- |
| `CWS_CLIENT_ID`, `CWS_CLIENT_SECRET` | A Google Cloud project → enable *Chrome Web Store API* → OAuth client (Desktop app). |
| `CWS_REFRESH_TOKEN` | A one-time OAuth consent for scope `https://www.googleapis.com/auth/chromewebstore` with that client, run as the publisher account. |
| `CWS_PUBLISHER_ID` | Developer dashboard → Account page. |
| `CWS_EXTENSION_ID` | The item id from step 1. |

Add them with `gh secret set <NAME> -R <owner>/<repo>` (each prompts for the value, so nothing lands in
shell history). Without them the workflow still builds the release and skips the upload.

## 3. Microsoft Edge Add-ons (optional)

The same store zip runs unchanged on Edge. The full steps are in
[`extension/store/README.md` § Microsoft Edge Add-ons](../extension/store/README.md#microsoft-edge-add-ons-optional):
Partner Center (free) → upload → visibility **Hidden** → paste the listing copy and test notes → submit.
After approval, in a PR: `[edge_add_ons] url` (`https://microsoftedge.microsoft.com/addons/detail/…`) +
`product_id`. The setup dialog then adds **Add to Edge**. Edge uploads stay manual; the workflow only
uploads to Chrome.

## 4. Every later release

1. In a PR: `--bump patch|minor` (the store refuses a version that isn't higher), merge.
2. Tag `companion-v<version>` and push the tag. The workflow builds the zips and the GitHub release,
   plus the Chrome draft if the secrets exist.
3. Chrome dashboard: upload the store zip (or open the draft) → **Submit**. Edge: Partner Center →
   *Packages* → upload → **Publish**.
4. If the change adds a permission or host, update `listing.md`'s justifications first. A new
   permission also re-prompts existing users.
