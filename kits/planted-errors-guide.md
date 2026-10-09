# Planted errors: how to prepare and seal them

*Paper: Section 5.2 (Week and above need a planted error in the window) and Table 3.*
*For: reviewers, team leads and auditors who prepare tasks for Week-size pieces and above.*

A planted error is a deliberate fault put into the task material before the hand-over. If the person
accepts the result without finding it, the check was not really done. Any missed planted error makes
the piece unverified and blocks Week and above in that window.

## 1. What makes a good planted error
- **Plausible.** It looks like a mistake a real source would contain, in the language of the domain.
- **Consequential.** If it passed into the result, a user would be harmed or misled.
- **Checkable.** There is one clear way to tell whether it was caught (removed, flagged or corrected).
- **Not findable by search.** It is not a famous error or a copy of a public example.

## 2. Examples by domain (adapt, never reuse publicly)
| Domain | Example of a planted error |
|---|---|
| Bookkeeping | One invoice dated in the wrong fiscal year, inside a batch of correct ones |
| Contracts | A notice period in one clause that contradicts the schedule |
| Data analysis | A duplicated block of rows that inflates one region's total |
| Marketing | A price in the brief that does not match the price list |
| Software | A requirement that two documents state differently |
| Research summary | A cited figure that the cited source does not contain |

## 3. Sealing
1. The preparer writes the list: where each error is, what "caught" means.
2. The list is hashed (`shasum -a 256 planted.txt`) and the hash is written into the task record
   before the hand-over; the list itself goes to the auditor, not to the person.
3. After acceptance, the auditor opens the list, compares, and records `planted_errors` and
   `planted_missed` in the log line.
4. Errors are never reused across people in the same team.

## 4. How many
One to three per Week-size piece is enough. More turns the task into a puzzle and changes the work.
