---
target: Commanders view
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
timestamp: 2026-10-04T16-12-05Z
slug: web-src-views-compareview-tsx
---
Method: dual-agent (A: 640ed166 · B: 36d7c643)

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Function mode counts didn't explain multi-membership (fixed: helper line) |
| 2 | Match System / Real World | 4 | Ramp/Removal/Tutor = deckbuilder language |
| 3 | User Control and Freedom | 3 | URL-backed toggles; no reset |
| 4 | Consistency and Standards | 3 | Rows lacked the also-note (fixed, wide columns) |
| 5 | Error Prevention | 2 | Repeated cards misread as extra uniques (fixed: helper) |
| 6 | Recognition Rather Than Recall | 2 | "Function" unexplained (fixed: helper) |
| 7 | Flexibility and Efficiency | 3 | Dense rows/grid + URL state |
| 8 | Aesthetic and Minimalist Design | 2 | 13 EDHREC list chips exposed (>5 → MultiSelect, deferred to P1) |
| 9 | Error Recovery | 3 | No-tags note links to Jobs |
| 10 | Help and Documentation | 2 | Little contextual help |
| **Total** | | **27/40** | Good |

Design specificity: product-authored; function grouping fits the After-Hours Price Guide world. Detector: CLI 0 findings; in-page: cramped-padding×2, clipped-overflow (virtualizer, FP), single-font (intentional, FP), skipped-heading×3, layout-transition×1 — all pre-existing.

Priority issues: [P1] explain multi-membership (fixed); [P1] EDHREC list chip overload → MultiSelect (P1 branch owns Sidebar); [P2] rows lose also-note (fixed ≥24rem; preview carries functions); [P2] hover-only preview on touch (deferred); [P3] "EDHREC lists" Group-by label clashed with Filter chips (renamed "Card type").
