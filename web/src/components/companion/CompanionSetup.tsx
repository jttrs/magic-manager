import { Dialog } from 'radix-ui';
import { useState } from 'react';
import { useCompanion, type CompanionState } from '../../app/useCompanion';
import { Button } from '../Button';
import { iconActionClass } from '../iconActionClass';
import { IconTooltip } from '../IconTooltip';
import { CopyButton } from '../CopyButton';

/** Header status icon (companion flag): a dot for the state (amber connected,
 *  rust update, hollow not connected); opens setup — install, pair, what it may read. */
export function CompanionButton() {
  const c = useCompanion();
  const [open, setOpen] = useState(false);
  const v = c.hello?.version;
  const label = c.status === 'ready'
    ? (c.outdated ? `Browser companion · update available · v${v} → v${c.latest}` : `Browser companion · connected · v${v}`)
    : c.status === 'absent' ? 'Browser companion · set up · not connected' : 'Browser companion';
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <IconTooltip label={label}>
        <Dialog.Trigger aria-label={label} className={iconActionClass('chrome')}>
          <svg viewBox="0 0 16 16" aria-hidden="true" className="size-[1.125rem]">
            <path d="M6 2.5v3M10 2.5v3M4.5 5.5h7v2.5a3.5 3.5 0 0 1-7 0z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M8 11.5v2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          {c.status === 'ready' && (
            <span aria-hidden="true" className={`absolute right-1.5 top-1.5 size-2 rounded-pill ${c.outdated ? 'bg-danger' : 'bg-accent'}`} />
          )}
          {c.status === 'absent' && (
            <span aria-hidden="true" className="absolute right-1.5 top-1.5 size-2 rounded-pill border border-on-chrome-muted" />
          )}
        </Dialog.Trigger>
      </IconTooltip>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(52rem,calc(100dvh-1.5rem))] w-[min(44rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
            <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Browser companion</Dialog.Title>
            <Dialog.Description className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
              A Chrome extension that reads your carts, your open store tabs, Moxfield and Archidekt decks and your Moxfield collection in your own browser. Each time, it shows you exactly what it would send and waits for you to approve.
            </Dialog.Description>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            <Setup c={c} />
          </div>
          <div className="flex justify-end border-t border-rule px-5 py-3">
            <Dialog.Close asChild><Button tone="paper">Done</Button></Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const H3 = 'border-b border-rule-strong pb-1 text-md voice-condensed font-bold uppercase tracking-[0.04em] text-ink';

function Setup({ c }: { c: CompanionState }) {
  const origin = window.location.origin;
  return (
    <div className="flex flex-col gap-6">
      <Status c={c} />

      <section aria-labelledby="cmp-install" className="flex flex-col gap-3">
        <h3 id="cmp-install" className={H3}>{c.status === 'ready' ? 'Install on another browser' : 'Install'}</h3>
        {c.storeUrl ? (
          <div className="flex flex-col items-start gap-1.5">
            <a
              href={c.storeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-10 items-center gap-2 rounded-sm border border-accent bg-accent px-4 text-md voice-semi font-medium text-on-accent transition-[background-color] ease-guide hover:bg-highlight-solid"
            >
              Add to Chrome<span className="sr-only"> (opens the Chrome Web Store)</span>
            </a>
            <p className="text-sm text-ink-muted">From the Chrome Web Store. Chrome keeps it up to date.</p>
          </div>
        ) : (
          <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">The companion isn’t on the Chrome Web Store yet — install it with the developer install below.</p>
        )}
        <details open={!c.storeUrl} className="border-y border-rule py-2 text-md">
          <summary className="cursor-pointer voice-semi font-medium text-ink">Developer install</summary>
          <div className="mt-2 flex flex-col gap-2">
            {c.storeUrl && <p className="text-sm text-ink-muted">Only if you can’t use the store: the same extension, loaded by hand. It doesn’t update itself.</p>}
            <ol className="flex list-decimal flex-col gap-3 pl-5 leading-relaxed marker:text-ink-muted">
              <li>
                <a href="/api/companion/extension.zip" download className="font-medium text-ink underline decoration-accent underline-offset-2">Download the companion</a> (v{c.latest ?? '…'}) and unzip it.
              </li>
              <li>
                In Chrome, open <code className="tabular text-sm">chrome://extensions</code>, switch on <strong>Developer mode</strong>, press <strong>Load unpacked</strong> and choose the <code className="tabular text-sm">magic-manager-companion</code> folder. Then pair it as below.
                <span className="mt-1 flex"><CopyButton getText={() => 'chrome://extensions'} label="Copy chrome://extensions" tone="paper" /></span>
              </li>
            </ol>
            <p className="text-sm text-ink-muted">To update: download again, replace the folder, then press the reload arrow on the companion in <code className="tabular">chrome://extensions</code>.</p>
          </div>
        </details>
        <ol className="flex list-decimal flex-col gap-3 pl-5 text-md leading-relaxed marker:text-ink-muted">
          <li>
            Click the companion’s icon (pin it from Chrome’s puzzle-piece menu), enter this app’s address and press <strong>Pair</strong>:
            <span className="mt-1 flex flex-wrap items-center gap-2">
              <code className="rounded-xs bg-paper-sunk px-2 py-1 tabular text-sm">{origin}</code>
              <CopyButton getText={() => origin} label="Copy address" tone="paper" />
            </span>
          </li>
          <li>For more than your Mana Pool cart, switch on <strong>Allow access</strong> on the same page. Chrome asks once for all the sites it reads.</li>
          <li>Reload this page.</li>
        </ol>
      </section>

      <section aria-labelledby="cmp-reads" className="flex flex-col gap-1">
        <h3 id="cmp-reads" className={H3}>What it can read</h3>
        <Feature on={c.hello?.features.cart} name="Mana Pool cart" detail="Your cart page: each card’s printing, finish, condition, quantity and price. Always on." />
        <Feature on={c.hello?.features.deals} name="Deals — your open store tabs" detail="Which product pages you have open on the Deals stores, and the price on open-tab stores. Needs Allow access in the companion’s settings." />
        <Feature on={c.hello?.features.moxfield} name="Moxfield decks, collection and binders" detail="A deck, your collection or a binder you choose. Shared links are read without signing in; for your own private ones it uses Moxfield’s short-lived sign-in in that tab. Needs Allow access in the companion’s settings." />
        <Feature on={c.hello?.features.archidekt} name="Archidekt decks" detail="A deck you choose, as your browser sees it — including your own private decks when you’re signed in. Needs Allow access in the companion’s settings." />
      </section>

      <section aria-labelledby="cmp-never" className="flex flex-col gap-1">
        <h3 id="cmp-never" className={H3}>What it never does</h3>
        <ul className="flex list-disc flex-col gap-0.5 pl-5 text-md leading-relaxed">
          <li>Read cookies, passwords, email or addresses.</li>
          <li>Send a sign-in token anywhere. Moxfield’s own short-lived token, for your private Moxfield cards, stays in that Moxfield tab for the one read.</li>
          <li>Change anything on Mana Pool, Moxfield, Archidekt or a store — no cart edits, no purchases.</li>
          <li>Answer any website but this app, or send anything you haven’t approved.</li>
          <li>Collect in the background, run analytics, or load code from the internet.</li>
        </ul>
        <p className="text-sm text-ink-muted">
          The source is plain, readable JavaScript in the app’s repo under <code className="tabular">extension/</code>.
          {c.privacyUrl && <>{' '}<a href={c.privacyUrl} target="_blank" rel="noopener noreferrer" className="text-ink underline decoration-accent underline-offset-2">Privacy policy</a></>}
        </p>
      </section>
    </div>
  );
}

function Status({ c }: { c: CompanionState }) {
  if (c.status === 'checking') return <p role="status" className="text-md text-ink-muted">Looking for the companion on this page…</p>;
  if (c.status === 'absent') {
    const origin = window.location.origin;
    return (
      <div role="status" className="flex flex-col gap-2 text-md leading-relaxed">
        <p>
          <span className="font-medium">Not connected.</span>{' '}
          <span className="text-ink-muted">The companion must be paired with exactly this address. Paste it into the companion’s settings, press Pair, then reload this page.</span>
        </p>
        <span className="flex flex-wrap items-center gap-2">
          <code className="rounded-xs bg-paper-sunk px-2 py-1 tabular text-sm">{origin}</code>
          <CopyButton getText={() => origin} label="Copy this app’s address" tone="paper" />
        </span>
      </div>
    );
  }
  return (
    <div role="status" className="flex flex-col gap-1 text-md leading-relaxed">
      <p><span className="highlighter px-1 font-medium">Connected</span> <span className="tabular text-ink-muted">· version {c.hello!.version}</span></p>
      {c.outdated && (
        <p className="text-danger">
          {c.storeUrl
            ? <>Version {c.latest} is available. Chrome updates store installs on its own, usually within a few hours; a developer install needs the download below.</>
            : <>Version {c.latest} is available — download it below and replace the folder.</>}
        </p>
      )}
    </div>
  );
}

function Feature({ on, name, detail }: { on: boolean | undefined; name: string; detail: string }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-rule py-2">
      <div className="min-w-0 flex-1">
        <p className="text-md font-medium">{name}</p>
        <p className="text-sm leading-relaxed text-ink-muted">{detail}</p>
      </div>
      <span className={`shrink-0 text-sm voice-semi ${on ? 'text-ink' : 'text-ink-muted'}`}>{on == null ? '—' : on ? 'On' : 'Off'}</span>
    </div>
  );
}
