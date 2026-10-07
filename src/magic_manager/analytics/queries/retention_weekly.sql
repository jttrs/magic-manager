-- Weekly retention: users (pseudonymous keys) by first-active week × active week. Usage only.
WITH firsts AS (
    SELECT user_key, MIN(week) AS cohort
    FROM events
    WHERE user_key IS NOT NULL AND category = 'usage'
    GROUP BY user_key
),
active AS (
    SELECT DISTINCT user_key, week
    FROM events
    WHERE user_key IS NOT NULL AND category = 'usage'
)
SELECT f.cohort, a.week, COUNT(*) AS users
FROM firsts f
JOIN active a ON a.user_key = f.user_key
WHERE a.week >= :since
GROUP BY f.cohort, a.week
ORDER BY f.cohort, a.week
