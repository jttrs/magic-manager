-- The most frequent errors: event + its aggregate dims (route/status/code, job/code, view/kind/code…).
SELECT name, dims, SUM(n) AS n, MIN(day) AS first_seen, MAX(day) AS last_seen
FROM daily_counts
WHERE category = 'error' AND day >= :since
GROUP BY name, dims
ORDER BY n DESC, last_seen DESC
LIMIT :limit
