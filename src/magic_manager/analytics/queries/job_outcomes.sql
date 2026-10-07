-- Background jobs: runs, failures and mean duration of successful runs, per job.
SELECT j.value AS job,
       SUM(CASE WHEN e.name = 'job.started' THEN 1 ELSE 0 END) AS runs,
       SUM(CASE WHEN e.name = 'job.failed' THEN 1 ELSE 0 END) AS failures,
       AVG(CASE WHEN e.name = 'job.succeeded' THEN CAST(d.value AS INTEGER) END) AS mean_ms
FROM events e
JOIN event_props j ON j.event_id = e.event_id AND j.key = 'job'
LEFT JOIN event_props d ON d.event_id = e.event_id AND d.key = 'duration_ms'
WHERE e.name IN ('job.started', 'job.succeeded', 'job.failed') AND e.day >= :since
GROUP BY j.value
ORDER BY runs DESC, failures DESC
