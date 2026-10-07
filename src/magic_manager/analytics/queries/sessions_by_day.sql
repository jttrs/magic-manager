-- Distinct browser sessions per day (session ids are random, in-memory, per tab).
SELECT day, COUNT(DISTINCT session_id) AS sessions, COUNT(*) AS events
FROM events
WHERE session_id IS NOT NULL AND day >= :since
GROUP BY day
ORDER BY day
