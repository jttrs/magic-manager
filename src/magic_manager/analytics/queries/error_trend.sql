-- Errors per day, by event (daily aggregates: kept ~13 months, no user key).
SELECT day, name, SUM(n) AS n
FROM daily_counts
WHERE category = 'error' AND day >= :since
GROUP BY day, name
ORDER BY day, name
