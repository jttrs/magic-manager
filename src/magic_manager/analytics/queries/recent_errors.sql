-- The newest raw error events with their properties and linking IDs (raw errors: kept 30 days).
SELECT e.event_id, e.name, e.ts, e.ts_ms, e.request_id, e.session_id, p.key, p.value
FROM events e
LEFT JOIN event_props p ON p.event_id = e.event_id
WHERE e.event_id IN (
    SELECT event_id FROM events
    WHERE category = 'error' AND day >= :since
    ORDER BY ts_ms DESC
    LIMIT :limit
)
ORDER BY e.ts_ms DESC, e.event_id, p.key
