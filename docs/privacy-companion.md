# magic-manager companion — privacy policy

_Last updated: 2026-11-01 · applies to the "magic-manager companion" Chrome extension, version 0.5.0 and later._

The companion is a helper for **magic-manager**, a Magic: The Gathering collection manager you run
yourself or sign in to (on your own computer, or at an address someone who invited you runs). The extension reads card lists that only
your browser can see — your store carts, your open store tabs, your decks and collection on deck sites,
your store order history — and, **only after you approve each read in the extension's own window**,
hands the card lines to the magic-manager app you paired it with.

## Who runs it

magic-manager is an open-source project (<https://github.com/jttrs/magic-manager>). The extension has
no server of its own. Your data goes only to the magic-manager app **you** paired, at the address
**you** entered — your own, or a hosted magic-manager run by whoever invited you, who then holds the card
lines you approved (every approval window names that address).

## What it reads

Only when you ask for a read in your magic-manager app, and only on these sites:

| Read | Site | What is read |
| --- | --- | --- |
| Cart | Mana Pool (always), TCGplayer, Card Kingdom | Each cart line: card, printing, finish, condition, language, quantity, price |
| Open store tabs (Deals) | The card stores listed in the extension's settings | The address and title of each tab you have open on those stores (never other sites, never private windows), and on product pages their price and stock |
| Watched prices | The same stores | The price and stock on store pages you chose to watch |
| Decks | Moxfield, Archidekt | The deck you choose: card names, printings, quantities, boards |
| Collection and binders | Moxfield | Your collection or one binder you choose: printings, quantities, finishes |
| Order history | Mana Pool, TCGplayer, Card Kingdom | The orders you choose: order number, date, card lines, prices paid, shipping, tax and total |

Sites other than Mana Pool are read only after you switch on **Allow access** in the extension's
settings (Chrome asks you to confirm), and you can switch it off at any time.

## What it never reads or does

- It never reads cookies, passwords, payment details, email addresses or postal addresses.
- It never changes anything on a site: no cart edits, no purchases, no posts.
- It never reads in the background. Every read starts from your request and waits for you to press
  **Send to magic-manager** in its window. Close the window or press **Don’t send** and nothing is sent.
- It never answers any website except the one magic-manager address you paired.
- It never loads code from the internet, and it contains no analytics, tracking or advertising.

**One exception, for private Moxfield cards:** to read your own private Moxfield deck, collection or
binder, the extension uses Moxfield's own short-lived sign-in token inside that Moxfield tab for that
one read. The token is never stored, never sent to magic-manager and never sent anywhere else.

## Where data goes

- **To your magic-manager app only** — the one address you paired (this computer, or the https
  address you open your app at; every approval window names it). Only the normalized card lines you approved are sent.
- **Nowhere else.** The extension sends nothing to the developer, to Google, or to any third party,
  and nothing is sold or shared.

## What it stores in your browser

- `appOrigin` — the magic-manager address you paired (until you unpair or uninstall).
- `lastHello` — when that address last checked in, so the settings page can say whether pairing works.
- One pending read — held in Chrome's session memory only while it waits for your decision, then
  deleted. Session memory is cleared when Chrome closes.

Uninstalling the extension removes all of it.

## Your magic-manager app

What happens to the card lines once your app receives them is up to your app, which you run and
control: it stores them in your own collection database. The app's own optional, self-hosted error and
usage statistics are described in the app (Settings → Privacy) and never leave the app's host.

## Limited use

The use of information received from the extension adheres to the
[Chrome Web Store User Data Policy](https://developer.chrome.com/docs/webstore/program-policies/user-data-faq),
including the Limited Use requirements. Data is used only to provide the single purpose described
above — handing the card lines you approve to your own magic-manager app — and for no other purpose.

## Changes and contact

Changes to this policy are made in the project's repository, where the full history is public.
Questions: open an issue at <https://github.com/jttrs/magic-manager/issues>.

Technical detail (threat model, permissions, tests): [`browser-companion-security.md`](browser-companion-security.md).
