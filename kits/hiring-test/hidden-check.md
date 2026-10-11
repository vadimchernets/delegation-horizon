# Hidden check (never shown to the candidate)

**Task:** [name]   **Reference hours:** [geometric mean of two blind estimates within x1.5, or the median of three]   **Prepared by:** [name]   **Date:** [date]

## Acceptance criteria
| # | Criterion | How the reviewer tests it | Must pass? |
|---|---|---|---|
| 1 | | | yes |
| 2 | | | yes |
| 3 | | | no |

## Planted errors (sealed)
SHA-256 of the planted-error list, recorded before the first candidate starts (`python3 tools/planted.py seal`): [hash]

| # | Kind (wrong entry or omission) | Where | What it is | Counts as caught if |
|---|---|---|---|---|
| 1 | wrong entry | | | |
| 2 | omission | | | |

From Week upward at least one of the planted errors should be an omission, wherever the work has
something it must contain. This one-day test carries one as well, in row 2.
