import { Dialog, Tooltip } from 'radix-ui';
import { useState } from 'react';
import { useCompanion, type CompanionState } from '../../app/useCompanion';
import { Button } from '../Button';
import { CopyButton } from '../CopyButton';

/** Header icon (companion flag): opens setup — install, pair, what it may read. */
export function CompanionButton() {
  const c = useCompanion();
  const [open, setOpen] = useState(false);
  const label = c.status === 'ready' ? (c.outdated ? 'Browser companion · update available' : 'Browser companion · connected') : 'Browser companion · set up';
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Tooltip.Provider delayDuration={200}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <Dialog.Trigger asChild>
              <button
                type="button"
                aria-label={label}
                className="relative grid size-8 cursor-pointer place-items-center rounded-sm text-on-chrome-muted transition-colors ease-guide hover:text-on-chrome"
              >
                <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
                  <path d="M6 2.5v3M10 2.5v3M4.5 5.5h7v2.5a3.5 3.5 0 0 1-7 0z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M8 11.5v2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                {(c.status === 'ready' || c.outdated) && (
                  <span aria-hidden="true" className={`absolute right-1 top-1 size-1.5 rounded-pill ${c.outdated ? 'bg-danger' : 'bg-accent'}`} />
                )}
              </button>
            </Dialog.Trigger>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
              {label}
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(52rem,calc(100dvh-1.5rem))] w-[min(44rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
            <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Browser companion</Dialog.Title>
            <Dialog.Description className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
              A Chrome extension that reads your Mana Pool cart, your open store tabs and Moxfield decks in your own browser. Each time, it shows you exactly what it would send and waits for you to approve.
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

      <section aria-labelledby="cmp-install" className="flex flex-col gap-2">
        <h3 id="cmp-install" className={H3}>{c.status === 'ready' ? 'Install on another browser' : 'Install'}</h3>
        <ol className="flex list-decimal flex-col gap-3 pl-5 text-md leading-relaxed marker:text-ink-muted">
          <li>
            <a href="/api/companion/extension.zip" download className="font-medium text-ink underline decoration-accent underline-offset-2">Download the companion</a> (v{c.latest ?? '…'}) and unzip it.
          </li>
          <li>
            In Chrome, open <code className="tabular text-sm">chrome://extensions</code>, switch on <strong>Developer mode</strong>, press <strong>Load unpacked</strong> and choose the <code className="tabular text-sm">magic-manager-companion</code> folder.
            <span className="mt-1 flex"><CopyButton getText={() => 'chrome://extensions'} label="Copy chrome://extensions" tone="paper" /></span>
          </li>
          <li>
            Click the companion’s icon (pin it from Chrome’s puzzle-piece menu), enter this app’s address and press <strong>Pair</strong>:
            <span className="mt-1 flex flex-wrap items-center gap-2">
              <code className="rounded-xs bg-paper-sunk px-2 py-1 tabular text-sm">{origin}</code>
              <CopyButton getText={() => origin} label="Copy address" tone="paper" />
            </span>
          </li>
          <li>Reload this page.</li>
        </ol>
        <p className="text-sm text-ink-muted">To update: download again, replace the folder, then press the reload arrow on the companion in <code className="tabular">chrome://extensions</code>.</p>
      </section>

      <section aria-labelledby="cmp-reads" className="flex flex-col gap-1">
        <h3 id="cmp-reads" className={H3}>What it can read</h3>
        <Feature on={c.hello?.features.cart} name="Mana Pool cart" detail="Your cart page: each card’s printing, finish, condition, quantity and price. Always on." />
        <Feature on={c.hello?.features.deals} name="Deals — your open store tabs" detail="Which product pages you have open on the Deals stores, and the price on open-tab stores. Switch it on in the companion’s settings." />
        <Feature on={c.hello?.features.moxfield} name="Moxfield decks" detail="A deck you choose, as your browser sees it — including your own private decks when you’re signed in. Switch it on in the companion’s settings." />
      </section>

      <section aria-labelledby="cmp-never" className="flex flex-col gap-1">
        <h3 id="cmp-never" className={H3}>What it never does</h3>
        <ul className="flex list-disc flex-col gap-0.5 pl-5 text-md leading-relaxed">
          <li>Read cookies, passwords, sign-in tokens, email or addresses.</li>
          <li>Change anything on Mana Pool, Moxfield or a store — no cart edits, no purchases.</li>
          <li>Answer any website but this app, or send anything you haven’t approved.</li>
          <li>Collect in the background, run analytics, or load code from the internet.</li>
        </ul>
        <p className="text-sm text-ink-muted">The source is plain, readable JavaScript in the app’s repo under <code className="tabular">extension/</code>.</p>
      </section>
    </div>
  );
}

function Status({ c }: { c: CompanionState }) {
  if (c.status === 'checking') return <p role="status" className="text-md text-ink-muted">Looking for the companion on this page…</p>;
  if (c.status === 'absent') {
    return (
      <p role="status" className="text-md leading-relaxed">
        <span className="font-medium">Not connected.</span> <span className="text-ink-muted">Either it isn’t installed, it isn’t paired with {window.location.origin}, or this page was open before you paired — reload it.</span>
      </p>
    );
  }
  return (
    <div role="status" className="flex flex-col gap-1 text-md leading-relaxed">
      <p><span className="highlighter px-1 font-medium">Connected</span> <span className="tabular text-ink-muted">· version {c.hello!.version}</span></p>
      {c.outdated && <p className="text-danger">Version {c.latest} is available — download it below and replace the folder.</p>}
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
