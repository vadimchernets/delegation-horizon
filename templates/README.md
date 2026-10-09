# Templates

Three forms, each usable without writing any code.

| File | Who fills it | What it is for |
|---|---|---|
| `work-log.csv` | The person handing work to agents, or a team lead | One row per piece of work handed to agents. Open it in any spreadsheet, fill a row when a piece closes, save as CSV, run `record_card.py` |
| `task-card.md` | Whoever builds a task bank (an employer, a school, a research group) | One task of a frozen bank: what counts as done, measured by-hand time, hidden checks, planted errors |
| `guarantor-record.md` | A person who signs for products made by others | The guarantor's own track record (Section 7.2 of the paper): what they vouched for, how long it lived, what failed |

## The work log, column by column

Write a row when a piece is accepted, rejected or abandoned. Keep the failed and abandoned ones: they are part of
the score, and a log without them can lose a rung (the worked example in the paper shows how).

| Column | What to write | Example |
|---|---|---|
| person | A pseudonymous label, never a real name | P07 |
| domain | The field the work belongs to, the same words every time | small-business bookkeeping |
| started | Optional: the day you handed the piece over | 2026-09-10 |
| date | The day the piece was accepted, rejected or abandoned | 2026-09-14 |
| reference_hours | How long a qualified specialist would need by hand, for the whole deliverable | 8 |
| reference_basis | Where that number came from: a named task bank, or "two raters" | two raters |
| attention_minutes | Your own minutes: planning, instructing, reading, checking, fixing. Agent time while you do something else does not count | 95 |
| mode | `one_piece` (handed over at once), `stages`, or `together` (worked side by side) | stages |
| check | `hidden_tests`, `expert`, `real_use`, `other_family_with_sources`, `same_family`, `self_review` or `none` | expert |
| agent_saw_check | yes or no: could the agents see the check? | no |
| passed | yes or no (no for failed or abandoned pieces) | yes |
| irreversible | yes or no: can a mistake here be undone? (money moved, a filing that cannot be withdrawn) | no |
| planted_errors | How many errors were planted in the task before hand-over | 0 |
| planted_missed | How many of them you did not catch | 0 |
| outside_help | yes or no: did a colleague or contractor fix it off the log? | no |

Only four kinds of check can verify a piece: hidden tests, a qualified expert, real use by the intended users, and a
model of another family that checked against sources you opened. Self-review and agreement among models of one
family are recorded but never count.

Dates are written as year-month-day (2026-09-14). If your spreadsheet turns them into another format, set the
column to text before typing.
