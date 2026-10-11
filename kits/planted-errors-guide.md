# Planted errors: how to prepare and seal them

*Paper: Section 5.2 (Week and above need a planted error in the window), Table 3, Appendix A (a planted error is a wrong entry or an omission), Sections 6.5 and 10.5 (the two kinds are caught by different means).*
*For: reviewers, team leads and auditors who prepare tasks for Week-size pieces and above.*

A planted error is a deliberate fault put into the task material before the hand-over. If the person
accepts the result without finding it, the check was not really done. Any missed planted error, of
either kind, makes the piece unverified and blocks Week and above in that window.

## 1. Two kinds
The paper's glossary defines a planted error as an error placed in a task before hand-over, which the
person must catch, "either a wrong entry or an omission of something the work must contain" (Appendix A).
- **Wrong entry.** Something in the material is wrong: a figure, a date, a clause, a requirement. A careful
  reviewer can find it by reading what is there.
- **Omission.** Something the work must contain is missing from the material, so it will be missing from the
  result unless the person's process names it: a bill that was never accrued, a mandatory policy, a region
  left out of an extract. No reviewer is shown an omission. Only the person's knowledge of the trade, or a
  list of what the deliverable must contain drawn up before the work, names it (Section 6.5).

From Week upward, plant at least one omission wherever the work has something it must contain, and score
the two kinds apart. The list drawn up before the work is aimed at omissions and the reviewers at wrong
entries (Section 10.5), and models are far worse at noticing what is missing than at finding what is there
(Section 6.5), so catches of wrong entries say nothing about omissions.

## 2. What makes a good planted error
- **Plausible.** It looks like a mistake a real source would contain, in the language of the domain.
- **Consequential.** If it passed into the result, a user would be harmed or misled.
- **Checkable.** There is one clear way to tell whether it was caught (removed, flagged or corrected; for an
  omission, the missing item supplied or named as missing).
- **Not findable by search.** It is not a famous error or a copy of a public example.

## 3. Examples by domain (adapt, never reuse publicly)
| Domain | Wrong entry | Omission |
|---|---|---|
| Bookkeeping | One invoice dated in the wrong fiscal year, inside a batch of correct ones | A month-end close whose material leaves out an accrual for a known recurring bill |
| Contracts | A notice period in one clause that contradicts the schedule | A schedule that omits the notice address the clause requires |
| Data analysis | A duplicated block of rows that inflates one region's total | A region missing from the extract, with no row at all |
| Marketing | A price in the brief that does not match the price list | A brief that omits a mandatory pricing condition |
| Software | A requirement that two documents state differently | A requirement for input validation, stated nowhere in the ticket but in the domain rules |
| Research summary | A cited figure that the cited source does not contain | A source that contradicts the claim, left out of the material |
| Employee handbook | A leave entitlement below the legal minimum | A mandatory policy missing from the questionnaire (bank task LM10 plants three) |

## 4. Sealing
1. The preparer writes the list as a CSV with the columns `error_id,kind,where,what,caught_if`, where `kind` is
   `wrong_entry` or `omission`.
2. `python3 tools/planted.py seal planted.csv` prints the list's SHA-256 and its kinds. The hash is written into
   the task record (`templates/task-card.md`) before the hand-over; the list itself goes to the auditor, not to
   the person.
3. After acceptance, the auditor writes `outcome.csv` (`error_id,caught` with yes or no) and runs
   `python3 tools/planted.py score planted.csv outcome.csv --seal <hash>`. It refuses a list changed after sealing
   and prints `planted_errors` and `planted_missed` for the log line, with what was missed by kind. The kind
   is sealed with the error, so it cannot be changed once the result is seen.
4. Errors are never reused across people in the same team.

`caught` is yes when the person flagged or fixed the error before accepting the piece. An optional column of
`outcome.csv`, `caught_by`, records what caught it: `list` (the must-contain list, or a checklist written
before the work, named it), `own_reading`, `own_test` (a test or reconciliation the person ran),
`fresh_review` (a model of the same family in a fresh context), `other_family` (a model of another family
checking against sources the person opened) or `other`. The tool ignores the column; kept across pieces, it
shows which step catches which kind (`checking-process.md`).

## 5. How many
One to three per Week-size piece is enough, at least one of them an omission wherever the work has something it
must contain. More turns the task into a puzzle and changes the work.
