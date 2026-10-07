import { Popover, Tooltip } from 'radix-ui';
import { CopyTargets } from '../../components/CopyButton';
import { buyListTargets, type BuyStore } from '../../components/buyTargets';
import { BuyListMark } from '../../components/StoreMarks';
import { collectionBuyList, type SceneFinishOut, type SceneOut } from '../../core/api';
import { FINISH_LABEL, finishTally, isComplete, missingLine, sceneBuyItems, sceneByline, scenePct } from '../../core/scenes';

/** Beside a scene's name: artist + collector-number run, and how much of it you hold. */
export function SceneDetail({ scene }: { scene: SceneOut }) {
  const pct = scenePct(scene);
  return (
    <>
      <span className="hidden min-w-0 truncate text-sm normal-case text-ink-muted @[40rem]:inline">{sceneByline(scene)}</span>
      <span className="flex shrink-0 items-center gap-2" role="img" aria-label={`${pct}% of this ${scene.kind} owned in some finish`}>
        <span className="relative h-1.5 w-14 overflow-hidden rounded-pill bg-rule">
          <span className="absolute inset-y-0 left-0 bg-highlight-solid" style={{ width: `${pct}%` }} />
        </span>
        <span className="text-sm tabular text-ink">{pct}%</span>
      </span>
    </>
  );
}

/** Right side of a scene's head: per-finish completion + cost to finish, and the buy lists. */
export function SceneMeta({ scene }: { scene: SceneOut }) {
  return (
    <span className="flex items-center gap-4">
      {scene.finishes.map((f) => (
        <span key={f.finish} className={`hidden whitespace-nowrap text-sm tabular @[52rem]:inline ${isComplete(f) ? 'text-ink-muted' : 'text-ink'}`}>
          <span className="mr-1.5 text-xs voice-semi font-medium uppercase tracking-[0.06em] text-ink-muted">{FINISH_LABEL[f.finish]}</span>
          {finishTally(f)}
        </span>
      ))}
      <SceneBuy scene={scene} />
    </span>
  );
}

function buyText(f: SceneFinishOut, target: BuyStore) {
  return async () => {
    const r = await collectionBuyList({ body: { target, items: sceneBuyItems(f) } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };
}

/** Buy-list popover: one store strip per finish, since a scene is assembled in one finish. */
function SceneBuy({ scene }: { scene: SceneOut }) {
  const label = `Buy lists for ${scene.name}`;
  return (
    <Popover.Root>
      <Tooltip.Provider delayDuration={200}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <Popover.Trigger
              aria-label={label}
              className="touch-hit grid size-7 cursor-pointer place-items-center rounded-sm text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk data-[state=open]:bg-paper-sunk"
            >
              <BuyListMark className="size-[1.15rem]" />
            </Popover.Trigger>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 max-w-[16rem] rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm leading-snug text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
              {label}
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label={label}
          className="z-50 flex w-[min(22rem,calc(100vw-1.5rem))] flex-col gap-3 rounded-sm border border-chrome-line bg-chrome-raised p-3 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
        >
          <p className="m-0 text-on-chrome">
            <span className="voice-semi font-medium">{scene.name}</span>
            <span className="block text-xs text-on-chrome-muted">Assemble a {scene.kind} in one finish so the panels match. One copy of each missing printing.</span>
          </p>
          {scene.finishes.map((f) => (
            <section key={f.finish} aria-label={FINISH_LABEL[f.finish]} className="flex flex-col gap-1.5">
              <h4 className="m-0 flex items-baseline justify-between gap-2 text-xs voice-semi font-medium uppercase tracking-[0.06em] text-on-chrome-muted">
                {FINISH_LABEL[f.finish]}
                <span className="text-sm normal-case tracking-normal tabular text-on-chrome">{missingLine(f)}</span>
              </h4>
              {f.missing_ids.length > 0 && (
                <CopyTargets targets={buyListTargets((s) => buyText(f, s))} />
              )}
            </section>
          ))}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
