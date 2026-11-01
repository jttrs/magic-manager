import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Outlet, redirect, stripSearchParams } from '@tanstack/react-router';
import { AppShell } from '../components/AppShell';
import { collectionSearch, compareSearch, decksSearch, marketSearch } from '../core/search';
import { historySearch } from '../core/history';
import { jumpstartToDecks, legacyJumpstartSearch } from '../core/jumpstart';
import { analyticsSearch } from '../core/analyticsDashboard';
import { adminSearch } from '../core/admin';

const rootRoute = createRootRoute({
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/collection' });
  },
});

const exploreRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/explore',
  validateSearch: compareSearch,
  // Keep links short: defaults never appear in the URL.
  search: { middlewares: [stripSearchParams(compareSearch.parse({}))] },
  // Views load on demand (code-split); they reach route state via getRouteApi, so
  // there is no router↔view import cycle.
  component: lazyRouteComponent(() => import('../views/ExploreView'), 'ExploreView'),
});

// Commanders grew into Explore (any card, as a commander or as one of the 99).
const legacyCommandersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/commanders',
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/explore', search: { ...(search as object), role: 'commander' } as never });
  },
});

const collectionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/collection',
  validateSearch: collectionSearch,
  search: { middlewares: [stripSearchParams(collectionSearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/CollectionView'), 'CollectionView'),
});

const historyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/collection/history',
  validateSearch: historySearch,
  search: { middlewares: [stripSearchParams(historySearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/HistoryView'), 'HistoryView'),
});

// Jumpstart packs are deck recipes now: old Collection → Jumpstart links open them in Decks.
const legacyJumpstartRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/collection/jumpstart',
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/decks', search: jumpstartToDecks(legacyJumpstartSearch.parse(search)) as never });
  },
});

// The old missing-set view lived at /sets; it is now a filter of Collection.
const legacySetsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sets',
  beforeLoad: ({ search }) => {
    const families = (search as { families?: unknown }).families;
    throw redirect({ to: '/collection', search: { families: Array.isArray(families) ? families.map(String) : [], show: ['missing'] } as never });
  },
});

const decksRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/decks',
  validateSearch: decksSearch,
  search: { middlewares: [stripSearchParams(decksSearch.parse({}))] },
  // Old `built=true` links: only built recipes.
  beforeLoad: ({ search }) => {
    if (search.built) throw redirect({ to: '/decks', search: { ...search, built: undefined, own: ['built'] } as never, replace: true });
  },
  component: lazyRouteComponent(() => import('../views/DecksView'), 'DecksView'),
});

const deckEditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/decks/$slug/edit',
  component: lazyRouteComponent(() => import('../views/DeckEditorView'), 'DeckEditorView'),
});

const marketRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/market',
  validateSearch: marketSearch,
  search: { middlewares: [stripSearchParams(marketSearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/MarketView'), 'MarketView'),
});

const jobsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/jobs',
  component: lazyRouteComponent(() => import('../views/JobsView'), 'JobsView'),
});

const analyticsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analytics',
  validateSearch: analyticsSearch,
  search: { middlewares: [stripSearchParams(analyticsSearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/AnalyticsView'), 'AnalyticsView'),
});

// Hosted, admins only (the server refuses everyone else): people, invites, per-person flags.
const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/admin',
  validateSearch: adminSearch,
  search: { middlewares: [stripSearchParams(adminSearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/AdminView'), 'AdminView'),
});

export const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute, collectionRoute, historyRoute, legacyJumpstartRoute, legacySetsRoute, decksRoute, deckEditRoute, exploreRoute, legacyCommandersRoute, marketRoute, jobsRoute, analyticsRoute, adminRoute]),
  defaultPreload: 'intent',
});

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
