import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Outlet, redirect, stripSearchParams } from '@tanstack/react-router';
import { AppShell } from '../components/AppShell';
import { cardDiffSearch, compareSearch } from '../core/search';

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
    throw redirect({ to: '/commanders' });
  },
});

const compareRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/commanders',
  validateSearch: compareSearch,
  // Keep links short: defaults never appear in the URL.
  search: { middlewares: [stripSearchParams(compareSearch.parse({}))] },
  // Views load on demand (code-split); they reach route state via getRouteApi, so
  // there is no router↔view import cycle.
  component: lazyRouteComponent(() => import('../views/CompareView'), 'CompareView'),
});

const cardDiffRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sets',
  validateSearch: cardDiffSearch,
  search: { middlewares: [stripSearchParams(cardDiffSearch.parse({}))] },
  component: lazyRouteComponent(() => import('../views/CardDiffView'), 'CardDiffView'),
});

const jobsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/jobs',
  component: lazyRouteComponent(() => import('../views/JobsView'), 'JobsView'),
});

export const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute, compareRoute, cardDiffRoute, jobsRoute]),
  defaultPreload: 'intent',
});

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
