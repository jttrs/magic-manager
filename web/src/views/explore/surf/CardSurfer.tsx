import { useInfiniteQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { unwrap } from '../../../app/queries';
import { ViewLayout } from '../../../components/AppShell';
import { Button } from '../../../components/Button';
import { IconAction } from '../../../components/IconAction';
import { GuideSheet } from '../../../components/States';
import { ScryfallMark, ShuffleMark } from '../../../components/StoreMarks';
import { surfDraw, type SurfDrawOut } from '../../../core/api';
import { fmtInt } from '../../../core/format';
import { activeFilters, decodeSurf, drawRequest, encodeSurf, EMPTY_FILTERS, feedCards, feedEnd, feedSummary, nextPage, scryfallSearchUrl, type Page, type SurfState } from '../../../core/surf';
import { SurfCardEntry } from './SurfCardEntry';
import { SurfFilterRail } from './SurfFilterRail';

/** How long a j/k smooth scroll is treated as still on its way. */
const STEP_MS = 700;
const newSeed = () => Math.floor(Math.random() * 2 ** 31);

/** Explore → Surfer: an endless feed of random cards — art first, then flavor
 *  text, artist and printing — with the filters in the rail. Filters live in
 *  the URL (`surf`). */
export function CardSurfer({ raw, onChange, tabs }: { raw: string | undefined; onChange: (raw: string | undefined) => void; tabs: ReactNode }) {
  const state = useMemo(() => decodeSurf(raw), [raw]);
  const key = encodeSurf(state);
  const set = (s: SurfState) => {
    const next = encodeSurf(s);
    onChange(next === 'on' ? undefined : next);
  };
  const [seed, setSeed] = useState(newSeed);
  const scroller = useRef<HTMLDivElement>(null);
  const sentinel = useRef<HTMLDivElement>(null);

  const feed = useInfiniteQuery({
    queryKey: ['surf', 'draw', key, seed],
    queryFn: async ({ pageParam, signal }) => unwrap(await surfDraw({ body: drawRequest(state, seed, pageParam), signal })),
    initialPageParam: { offset: 0, first: true } as Page,
    getNextPageParam: (_last: SurfDrawOut, pages: SurfDrawOut[]) => nextPage(pages),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const pages = useMemo(() => feed.data?.pages ?? [], [feed.data]);
  const cards = useMemo(() => feedCards(pages), [pages]);
  const total = pages[0]?.total;
  const query = pages[0]?.query;
  const { hasNextPage, isFetchingNextPage, isError, fetchNextPage } = feed;

  // Focus the feed so j/k step cards straight away.
  useEffect(() => {
    scroller.current?.focus({ preventScroll: true });
  }, []);

  // A new filter or shuffle starts the feed from the top.
  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [key, seed]);

  // A page can come back empty yet not exhausted (your cards scan a slice at a
  // time): keep drawing until something shows or the server says it's done.
  useEffect(() => {
    if (!feed.isPending && !cards.length && hasNextPage && !isFetchingNextPage && !isError) void fetchNextPage();
  }, [feed.isPending, cards.length, hasNextPage, isFetchingNextPage, isError, fetchNextPage]);

  // Endless: draw the next few cards well before the reader reaches the end.
  useEffect(() => {
    const root = scroller.current;
    const el = sentinel.current;
    if (!root || !el || !hasNextPage) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && !isFetchingNextPage && !isError) void fetchNextPage();
    }, { root, rootMargin: '0px 0px 150% 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, [cards.length, hasNextPage, isFetchingNextPage, isError, fetchNextPage]);

  // The card a j/k scroll is heading to, so a key pressed mid-scroll steps on from there.
  const heading = useRef<{ at: number; when: number } | null>(null);
  const step = (dir: 1 | -1) => {
    const root = scroller.current;
    if (!root) return;
    const items = [...root.querySelectorAll<HTMLElement>('[data-surf-card]')];
    const top = root.getBoundingClientRect().top;
    const pending = heading.current && performance.now() - heading.current.when < STEP_MS ? heading.current.at : null;
    const at = pending ?? Math.max(0, items.findIndex((el) => el.getBoundingClientRect().bottom > top + 8));
    const next = Math.max(0, Math.min(items.length - 1, at + dir));
    const el = items[next];
    if (!el) return;
    heading.current = { at: next, when: performance.now() };
    // Scroll the feed only: scrollIntoView would also scroll the page, pushing the tabs away.
    root.scrollTo({ top: root.scrollTop + el.getBoundingClientRect().top - top, behavior: 'smooth' });
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === 'j') step(1);
    else if (e.key === 'k') step(-1);
  };

  const addTag = (slug: string) => set({ ...state, filters: { ...state.filters, art: [...new Set([...state.filters.art, slug])] } });
  const active = activeFilters(state.filters);

  const summary = feed.isPending ? 'Drawing random cards…' : feedSummary(state.source, total, cards.length, fmtInt);
  const actions = (
    <>
      <IconAction label="Shuffle — start a fresh feed" Icon={ShuffleMark} onClick={() => setSeed(newSeed())} />
      {query && state.source === 'scryfall' && (
        <a
          href={scryfallSearchUrl(query)}
          target="_blank"
          rel="noreferrer"
          aria-label="Open this search on Scryfall"
          title="Open this search on Scryfall"
          className="touch-hit grid size-9 place-items-center rounded-sm text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
        >
          <ScryfallMark className="size-[1.35rem]" />
        </a>
      )}
    </>
  );

  return (
    <ViewLayout label="Card surfer filters" summary={active > 0 ? `${fmtInt(active)} ${active === 1 ? 'filter' : 'filters'}` : undefined} sidebar={<SurfFilterRail state={state} onChange={set} />}>
      <GuideSheet title="Card surfer" nav={tabs} summary={<span role="status">{summary}</span>} actions={actions} actionsLabel="Card surfer actions">
        <div
          ref={scroller}
          tabIndex={0}
          role="feed"
          aria-label="Random cards"
          aria-busy={feed.isFetching}
          onKeyDown={onKey}
          className="h-[calc(100dvh-12rem)] snap-y snap-proximity overflow-y-auto overscroll-contain focus:outline-none lg:h-full [&>article]:min-h-full"
        >
          {feed.isPending ? (
            <Skeleton />
          ) : feed.isError && !pages.length ? (
            <FeedNote title="Couldn’t draw cards">
              {(feed.error as Error).message}
              <Button tone="paper" className="mt-3" onClick={() => feed.refetch()}>Try again</Button>
            </FeedNote>
          ) : !cards.length && (hasNextPage || isFetchingNextPage) && !isError ? (
            <FeedNote title={state.source === 'owned' ? 'Searching your cards…' : 'Drawing random cards…'}>
              <span role="status">This can take a moment.</span>
            </FeedNote>
          ) : !cards.length ? (
            <FeedNote title={state.source === 'owned' ? 'None of your cards match' : 'No cards match'}>
              Loosen a filter{active > 0 ? ' or start over' : ''}.
              {active > 0 && <Button tone="paper" className="mt-3" onClick={() => set({ ...state, filters: EMPTY_FILTERS })}>Reset filters</Button>}
            </FeedNote>
          ) : (
            <>
              {cards.map((c, i) => (
                <SurfCardEntry key={c.scryfall_id} card={c} eager={i < 2} onTag={addTag} />
              ))}
              <div ref={sentinel} className="flex min-h-24 flex-col items-center justify-center gap-3 px-4 pb-12 text-center text-sm text-ink-muted">
                {isFetchingNextPage ? (
                  <span role="status">Drawing more cards…</span>
                ) : feed.isFetchNextPageError ? (
                  <>
                    <span>Couldn’t draw more: {(feed.error as Error).message}</span>
                    <Button tone="paper" onClick={() => void fetchNextPage()}>Try again</Button>
                  </>
                ) : !hasNextPage ? (
                  <>
                    <span>
                      {feedEnd(pages) === 'all'
                        ? <>That’s every card that matches — {fmtInt(cards.length)} {cards.length === 1 ? 'card' : 'cards'}.</>
                        : <>Random draws keep repeating — {fmtInt(cards.length)} of {fmtInt(total ?? cards.length)} matches seen.</>}
                    </span>
                    <Button tone="paper" onClick={() => setSeed(newSeed())}>Shuffle and start again</Button>
                  </>
                ) : null}
              </div>
            </>
          )}
        </div>
      </GuideSheet>
    </ViewLayout>
  );
}

function FeedNote({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto flex max-w-[40ch] flex-col items-center px-4 py-24 text-center">
      <h3 className="text-2xl voice-condensed font-bold uppercase">{title}</h3>
      <div className="mt-2 flex flex-col items-center text-md leading-relaxed text-ink-muted">{children}</div>
    </div>
  );
}

function Skeleton() {
  return (
    <div role="status" aria-label="Drawing random cards" className="grid min-h-full content-center justify-items-center gap-x-12 gap-y-6 px-4 py-8 lg:grid-cols-[auto_minmax(16rem,32rem)] lg:justify-center lg:justify-items-start">
      <div className="aspect-[488/680] w-[min(100%,calc((100dvh-19rem)*0.7176),30rem)] lg:w-[min(calc((100dvh-19rem)*0.7176),30rem)] animate-pulse rounded-[4.5%/3.2%] bg-paper-sunk motion-reduce:animate-none" />
      <div className="flex w-full max-w-[30rem] flex-col gap-3">
        <div className="h-8 w-2/3 rounded-xs bg-paper-sunk" />
        <div className="h-4 w-1/2 rounded-xs bg-paper-sunk" />
        <div className="mt-4 h-4 w-full rounded-xs bg-paper-sunk" />
        <div className="h-4 w-5/6 rounded-xs bg-paper-sunk" />
      </div>
    </div>
  );
}
