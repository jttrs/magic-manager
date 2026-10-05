import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Outlet, redirect, stripSearchParams } from '@tanstack/react-router';
import { AppShell } from '../components/AppShell';
import { collectionSearch, compareSearch, decksSearch, marketSearch } from '../core/search';

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

export const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute, collectionRoute, legacySetsRoute, decksRoute, deckEditRoute, exploreRoute, legacyCommandersRoute, marketRoute, jobsRoute]),
  defaultPreload: 'intent',
});

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
