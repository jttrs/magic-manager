---
target: Collection view
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
timestamp: 2026-10-04T16-24-57Z
slug: web-src-views-collectionview-tsx
---
Method: dual-agent (A: critique-a 4b31168d · B: critique-b df78eb77)

## Design Health Score — 26/40
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Counts/active nav strong; copy feedback quieter |
| 2 | Match system / real world | 3 | Sidebar still said "Sets" after the rename → fixed ("Scope") |
| 3 | User control & freedom | 3 | No global reset → fixed ("Reset filters") |
| 4 | Consistency & standards | 3 | "Compare controls" legacy label → fixed |
| 5 | Error prevention | 3 | Unscoped "Select all" over ~45 families → removed |
| 6 | Recognition vs recall | 3 | Sort hierarchy semantics implicit → helper line added |
| 7 | Flexibility & efficiency | 3 | URL state, presets, DnD + ▲▼; no saved views yet |
| 8 | Aesthetic & minimalist | 2 | Dense sidebar; missing-debt dominates → Shopping view preset |
| 9 | Error recovery | 2 | Generic export failure → guiding message |
| 10 | Help & documentation | 1 | No contextual help → basis hints, sort helper |

## Design specificity
Authored, product-specific (price-guide vocabulary, exact-printing facts, buy-list outputs). Miss was operational hierarchy under load.

## Detector (B)
CLI 0 findings. In-page: text-occlusion ×6 (MISSING over tags) → fixed by stacking holdings/tags; skipped-heading → fixed (h1/h2/h3 outline); single-font, layout-transition = intentional (brand rule; resizable columns). Contrast all ≥5.6:1. "Unnamed input" = false positive (label-wrapped).

## Priority issues (status)
- P1 mobile hides active filters → collapsed bar now shows a scope summary.
- P1 stale "Sets" IA label → "Scope".
- P2 family picker choice overload → selected pinned first; scoped bulk-select only.
- P2 sort builder expert-only → explanatory line.
- P2 missing debt shock → "Shopping view" (missing, no bulk/treatments/chase).

## Open
Saved views; grouped/recent families in the picker; keyboard shortcuts.
