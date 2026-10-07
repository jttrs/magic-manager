-- Funnel: sessions that opened Collection → of those, sessions that exported a buy-list afterwards.
WITH viewed AS (
    SELECT e.session_id, MIN(e.ts_ms) AS at
    FROM events e
    JOIN event_props p ON p.event_id = e.event_id AND p.key = 'view' AND p.value = 'collection'
    WHERE e.name = 'page.viewed' AND e.session_id IS NOT NULL AND e.day >= :since
    GROUP BY e.session_id
),
exported AS (
    SELECT DISTINCT v.session_id
    FROM viewed v
    JOIN events e ON e.session_id = v.session_id AND e.name = 'buylist.exported' AND e.ts_ms >= v.at
)
SELECT (SELECT COUNT(*) FROM viewed) AS viewed_collection,
       (SELECT COUNT(*) FROM exported) AS exported_buylist
