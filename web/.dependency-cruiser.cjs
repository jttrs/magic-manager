/**
 * Architecture guard (decision doc §18 — portability). `src/core` is the
 * framework-free layer (API client, URL schemas, view-model derivations) that a
 * future Svelte port keeps verbatim, so it must never import React, any UI
 * library, or the React layers above it.
 */
module.exports = {
  forbidden: [
    {
      name: 'core-is-framework-free',
      severity: 'error',
      comment: 'src/core must stay framework-free (portability boundary).',
      from: { path: '^src/core' },
      to: { path: ['^src/(app|components|views)', 'node_modules/(react|react-dom|@tanstack/react-|radix-ui|react-resizable-panels)'] },
    },
    {
      name: 'components-do-not-know-views-or-routes',
      severity: 'error',
      comment: 'Presentational components take props; they must not import views or the router setup.',
      from: { path: '^src/components' },
      to: { path: ['^src/views', '^src/app/router'] },
    },
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Generated client (src/core/api) has a type-only internal cycle we do not own.',
      from: { pathNot: '^src/core/api/' },
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.app.json' },
    tsPreCompilationDeps: true,
    exclude: { path: '\\.test\\.ts$' },
  },
};
