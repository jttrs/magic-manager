-- One row per session: first/last event time, event count, error count.
SELECT session_id, MIN(ts_ms) AS start_ms, MAX(ts_ms) AS end_ms, COUNT(*) AS events,
       SUM(CASE WHEN category = 'error' THEN 1 ELSE 0 END) AS errors
FROM events
WHERE session_id IS NOT NULL AND day >= :since
GROUP BY session_id
ORDER BY start_ms
