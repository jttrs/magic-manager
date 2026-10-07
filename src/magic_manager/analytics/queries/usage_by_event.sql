-- Usage events by event + aggregate dims (page views per view/viewport, deck actions, buy-lists…).
SELECT name, dims, SUM(n) AS n, MAX(day) AS last_seen
FROM daily_counts
WHERE category = 'usage' AND day >= :since
GROUP BY name, dims
ORDER BY n DESC
