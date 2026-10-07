# Analytics — self-hosted product analytics and error telemetry

**Why.** Two owner goals: make development decisions from how the app is really
used, and catch common failures before anyone has to report them. Errors are the
first consumer. Everything is self-hosted — our own event store, our own
dashboards, no third-party scripts or SaaS.

**Binding principle** (owner, §25.0 of `docs/webapp-architecture-decision.md`):
*"we should also be very aware of security concerns users may have and develop in
a way that we cannot be used by a malicious actor to harm our users."* Every
choice below is held to it: record the minimum a product question needs, never
anything a user typed, and make it impossible to accidentally record more.

## Shape

```
browser (web/src/core/analytics.ts)        server (FastAPI)                         analytics.db (separate file)
  page.viewed, client.error, …  ── batch ─▶ POST /api/analytics/events ─┐
  X-MM-Session: <in-memory uuid> ─────────▶ every /api request           │  catalog.validate ─▶ consent ─▶ store.insert
                                            TelemetryMiddleware ─────────┤   (unknown events rejected,      events / event_props
                                              api.error, route triggers  │    unknown props dropped)        daily_counts (aggregate)
                                            JobManager ── job.* ─────────┘
                                                                        dashboards: saved SQL (analytics/queries/*.sql)
                                                                          → GET /api/analytics/summary (flag `analytics`) → Analytics view
                                                                          → `uv run mm analytics …` → DuckDB / notebooks
```

| Piece | Where |
|---|---|
| Event catalog (the contract) | `config/analytics_events.toml` |
| Engine | `src/magic_manager/analytics/` — `catalog` (validate), `store` (separate SQLite file, retention, forget), `consent`, `identity` (HMAC key), `dashboard` (runs saved SQL) |
| Saved, portable SQL | `src/magic_manager/analytics/queries/*.sql` |
| Request ids, coded errors, server events | `src/magic_manager/web/telemetry.py`; job events in `web/runtime.py` |
| API | `src/magic_manager/api/analytics.py` + `web/analytics_routes.py` |
| Client tracker | `web/src/core/analytics.ts` (framework-free) + `web/src/app/analytics.ts` (wiring) |
| Dashboard | Analytics view (`/analytics`, internal flag `analytics`) + `uv run mm analytics …` |

## Storage and linking (owner decision 2026-10-07 — §25 H14)

- **A separate store, everywhere.** Locally and when hosted on the owner's home
  server it is a separate SQLite file, `analytics.db`, beside the collection DB
  (`MM_ANALYTICS_DB` overrides). It is never the collection DB. It has its own
  tiny schema version (`meta.schema_version`), so it needs no collection
  migration. It is disposable (delete it and it is recreated empty). It is not
  in the undo snapshot (`undo.USER_TABLES`) or in `db/bak` backups. After a later
  vendor move it becomes its own database with its own role. A columnar store
  (ClickHouse, or DuckDB over Parquet) comes only if volume demands it.
- **Portable SQL** keeps that swap a backend change rather than a schema rethink.
  Timestamps are stored as ISO text plus integer epoch ms. Day and week buckets
  are columns. Properties live in a long `event_props (event_id, key, value)`
  table. The saved queries use no SQLite-only functions (a test enforces this).
- **Linked to app data only by IDs, never copied data:**
  - `event_id`: a UUID per event.
  - `session_id`: a random UUID the browser holds in memory per tab. It is never
    stored on the device and rotates after 30 idle minutes.
  - `request_id`: a 32-hex id per API request. It is returned as `X-Request-ID`
    and in every error body, written to the server log, and stored on the
    request's events, so an error a user sees can be traced (`mm analytics trace <ref>`).
  - App record ids where a question needs them: `job_id` today, and `ingest_id`
    is a declared type for later. Deck slugs are **not** recorded, because a user
    names them.
  - A **pseudonymous user key**, `HMAC-SHA256(user_id, server secret)`, which is
    one-way. Re-identifying it needs both the app's user table and the secret.
    The secret comes from `MM_ANALYTICS_SECRET` (the host's secret store), else a
    random per-install `analytics.secret` (mode 0600) beside the *collection* DB,
    never beside `analytics.db`. Rotating the secret makes older keys
    unlinkable, which anonymizes them (`key_version` records which secret made
    each key). Local mode has one user, `local`.
- **Delete-my-data:** the app computes the user's key and deletes their raw
  events (`DELETE /api/analytics/my-data`, `mm analytics forget`). Daily
  aggregates carry no user key and stay.
- **Access:** dashboard and analysis roles read `analytics.db` only and never the
  collection DB. Joins to app data happen only through the IDs above, under
  controlled access. When hosted, the dashboard is admin-only (flag `analytics`).

## Consent (owner decision; legal basis below)

Consent is split by purpose and stored in the collection DB's `settings` table
(`analytics.consent`). That is a user table, so in the hosted layout (§25 H1) it
lives in that user's own file.

| Purpose | Category | Local mode | Hosted (`MM_MODE=hosted`) |
|---|---|---|---|
| Errors / reliability | `error` | on, opt-out | **on, opt-out** (legitimate interest; shown in a notice) |
| Usage analytics | `usage` | on, opt-out | **off until the user opts in** (asked once at first login, changeable any time) |

- The browser stores no identifier before consent. The session id lives in
  memory only, and no cookie or localStorage is used for analytics.
- Consent is enforced **on the server** (client and server events alike), not
  just in the browser.
- `MM_ANALYTICS=off` disables all recording, for CI, demos, and the test suite
  by default.
- The choice is in the app (the masthead's *Privacy* control) and on the CLI:
  `mm analytics consent --no-usage`.

**Legal basis (research summary, not legal advice).**

- **CCPA/CPRA:** doesn't apply. The thresholds are $25M revenue, 100k
  Californians, or 50% of revenue from selling data.
- **GDPR:** applies if an invited user is in the EU or UK. A pseudonymous key is
  still personal data.
  - Minimal, disclosed, objectable error logging is commonly run under
    *legitimate interest*.
  - Usage analytics is safer with *consent*.
- **ePrivacy Art. 5(3):** needs consent before an identifier is stored on the
  device. We store none.
- **Local mode:** the owner's own use falls under GDPR's household exemption.
- **Before outside users:** re-check this with the §25.4 step-10 security review.

## Retention (automatic)

From `[retention]` in the catalog: raw **error** events 30 days, raw **usage**
events 90 days, **daily aggregates** about 13 months (396 days; they hold no user
key or session id). The server prunes at startup and then daily
(`web/app.py` lifespan). `mm analytics prune` runs it on demand.

## Catalog

`config/analytics_events.toml` is the only list of events the app may record.
Each event declares:

- a **version**, a **category** (error or usage) and a **source** (server or client);
- an **owner** and a **purpose**: the product question the event answers;
- typed **props**: `enum`, `int` (bounded), `code` (dotted snake_case, ≤ 64,
  no 5+ digit runs), `route` (an API route *name*, never a path), `view`
  (a fixed list), `job_id`, `ingest_id`. **There is no free-text type**;
- **dims**, the props rolled into the daily aggregate;
- optional **triggers**: API route names whose 2xx answer records the event with
  only the listed constant props. Nothing from the request body is recorded.

The server validates every event against the catalog. It rejects unknown events
(naming the reason), drops unknown or invalid properties, and rate-limits client
batches (50 per request, 600 events/min per process). It accepts client
timestamps only within the last 24 hours.

| Event | Category | Source | Properties | Purpose |
|---|---|---|---|---|
| `api.error` | error | server | `route`, `method`, `status`, `code` | Which API routes fail, with which status and error code, and how often. |
| `job.failed` | error | server | `job`, `code`, `duration_ms`, `job_id` | Which background jobs fail and why. |
| `client.error` | error | client | `view`, `kind`, `code` | Uncaught browser errors by view and error type (never the message). |
| `client.network_error` | error | client | `view`, `code` | API calls that never got an answer (offline, network, timeout). |
| `companion.error` | error | client | `code` | Coded browser-companion / bookmarklet failures — exactly the codes in `extension/errors.json` (`cart.page_changed`, `cart.empty`, `moxfield.private`, `request.denied`, …). |
| `page.viewed` | usage | client | `view`, `viewport` | Which views are used, on a narrow (phone) or wide screen. |
| `job.started` | usage | server | `job`, `job_id` | Which background jobs people run. |
| `job.succeeded` | usage | server | `job`, `duration_ms`, `job_id` | How long successful jobs take. |
| `deck.changed` | usage | server | `action` | Which deck actions people use. |
| `buylist.exported` | usage | server | `surface` | Whether buy-lists get used, and from which view. |
| `cards.added` | usage | server | — | How often cards are added through the web. |
| `checklist.saved` | usage | server | — | How often the web checklist replaces spreadsheet ingest. |
| `undo.restored` | usage | server | — | How often people need undo. |

`uv run mm analytics catalog` prints this table from the catalog. A test fails if
an event is missing from this doc.

**Adding an event:**

1. Add a catalog entry with a real product question as its `purpose`.
2. Add a row in the table above.
3. If it is client-sent, call `track()` from the view.
4. Bump `version` if a property's meaning changes.

Prefer a route trigger over client code for server-side outcomes.

## Errors are specific, never generic

- Every API error body is `{detail, code, request_id}`.
- `code` is the engine exception behind the HTTP error (`StaleCounts` →
  `stale_counts`), else `request_validation`, `not_found` or `http_<status>`.
- An unhandled exception becomes a **coded 500** that names the exception type
  (`"Unexpected server error — KeyError: …"`, `code: key_error`), never a bare
  "Internal Server Error".
- Failed jobs carry `error_code` beside the message.
- The web shows the request **ref** (the first 8 characters of `request_id`)
  next to an error, so a reported problem can be traced in seconds.

## Dashboards

- **In the app:** the Analytics view (`/analytics`, internal flag `analytics`)
  shows:
  - the error trend and top error groups (route/status/code, job/code,
    view/kind/code);
  - recent errors with their ref, and a ref lookup;
  - views used (wide vs narrow), feature use, sessions, the Collection →
    buy-list funnel, job outcomes, and the store/retention status.
- **CLI:** `uv run mm analytics summary | query <name> | sql <name> | trace <ref> | prune | consent | forget | catalog`.
- **Notebooks / DuckDB:** `mm analytics sql <name>` prints a saved query; the
  named params are `:since`, `:limit` and `:request_id`. For example:
  ```sql
  INSTALL sqlite; LOAD sqlite;
  ATTACH 'db/analytics.db' AS a (TYPE sqlite, READ_ONLY);
  USE a;
  -- paste a saved query, replacing :since with '2026-09-01'
  ```
  Saved queries:
  - `error_trend`, `top_errors`, `recent_errors`, `trace`;
  - `usage_by_event`, `sessions_by_day`, `session_lengths`;
  - `retention_weekly`, `funnel_collection_buylist`, `job_outcomes`.

## Threat model

| Threat | Mitigation |
|---|---|
| **The store leaks** (stolen backup, misconfigured access) | It holds no names, emails, card or collection contents, prices, URLs, free text, IPs or user agents, only catalog codes, coarse buckets (`viewport`), bounded ints and random/HMAC ids. Without the app DB *and* the secret, keys can't be tied to people. Short raw retention limits what a leak exposes. |
| **A malicious client poisons or floods events** | Server-side catalog validation (closed types, no free text), a batch cap, a per-process rate limit, a 24-hour timestamp window, and session ids accepted only as UUIDs. Client events can't claim to be server events. |
| **A developer accidentally records PII** (a new prop, an error message) | No free-text type exists. A `code` can't hold spaces, `@`, `/`, URLs, IPs or long digit runs. Error *messages* are never recorded, only exception class codes. The no-PII test suite fails on PII-named properties and on any type that accepts PII-shaped values. |
| **Re-identification by an analyst** | Analysts read `analytics.db` only. The HMAC secret lives in the host secret store or beside the collection DB, never with analytics. Rotating the secret severs old links. |
| **Cross-site tracking or third parties** | None. First-party endpoint, no third-party scripts, no cookies or device storage for analytics. |
| **A user is tracked without agreeing** | Consent is enforced server-side, usage is opt-in when hosted, there is an error opt-out, and a kill switch exists. Delete-my-data removes their raw events. |
| **Analytics breaks the app** | Recording never raises into a request or job. Writes run off the event loop on a separate file with a busy timeout, and pruning failures are logged, not fatal. |
| **Admin abuse when hosted** | The dashboard shows aggregates and pseudonymous keys only. There is no "act as user" and no join to collections through the app (§25.0). |
