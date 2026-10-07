-- Every event linked to one request id (or its prefix — the "ref" shown with an error in the app).
SELECT e.event_id, e.name, e.category, e.ts, e.request_id, e.session_id, p.key, p.value
FROM events e
LEFT JOIN event_props p ON p.event_id = e.event_id
WHERE e.request_id LIKE :request_id || '%'
ORDER BY e.ts_ms, e.event_id, p.key
