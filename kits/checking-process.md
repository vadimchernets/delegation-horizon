# Checking process: four steps for work in a field you are new to

*Paper: Section 6.5 (newcomers to a trade who check by process), Section 5.2 (what counts) and Table A4.*
*For: anyone handing work to agents in a field they are new to, whoever checks their log, and anyone else who wants the same steps.*

Experience used to supply three things: the making, a second look at what was made, and knowing what
the work must contain. Section 6.5 of the paper describes four steps that stand in for them. The
measure does not ask by which route the ability to check was acquired: if the work passes checks the
agents did not see, with omissions as well as wrong entries among the planted errors, a newcomer's
horizon rises like anyone's. Whether the steps close the gap with experience is not yet known;
`process-vs-experience-study.md` is the study that would show it, analysed with
`../tools/process_study.py`. This card sets out the steps, what each one earns in the log, and three
log lines that show it.

## The four steps

1. **Before the work, write the must-contain list.** Ask several models, of at least two families if
   you have them, what such a deliverable must contain, what is commonly forgotten and which checks
   apply. Merge the answers with what you know, and write the list on the acceptance card
   (`acceptance-card.md`) before the hand-over.
2. **One agent does the work,** given the task, the material and the list.
3. **A second review in a fresh context.** A new session that did not see how the work was made gets
   the result, the material and the list, not the conversation, and checks the result item by item.
   Treat its findings as leads to confirm: model critics also report faults that are not there
   (McAleese et al., 2024).
4. **A model of another family checks against sources you opened.** It compares the result with
   sources you opened yourself (the bank statement, the contract, the raw data, not an agent's summary
   of them) and leaves a written verdict. Keep the verdict.

## What each step stands in for, and what it earns

| Step | Stands in for (Section 6.5) | In the log (Section 5.2, Table A4) |
|---|---|---|
| 1. Must-contain list | Knowing what the work must contain | Part of the statement of done, not a check; it earns no credit on its own |
| 2. One agent | The making | The work that is checked |
| 3. Fresh review | A second look at what was made | A model of the same family is recorded as `same_family` and earns no credit, though it may improve the work before an independent check |
| 4. Another family | A second look at what was made | `other_family_with_sources`, only when it checked against sources you opened and its verdict can be audited. Never alone for irreversible work: there a hidden test or a qualified human is the default check, and another family a second line |

A piece counts toward a rung only through a check the agents did not see: hidden tests, a qualified
reviewer, real use by the intended users, or step 4 as above (Section 5.2). Steps 1 to 3 improve the
work and sharpen the check; they do not verify the piece.

The process costs attention. Log the minutes of all four steps: amplification gain counts them in its
denominator. From Week upward the window also needs a piece with planted errors, prepared and sealed by
someone else (`planted-errors-guide.md`).

## How to record it

1. One log line per piece, as usual (`templates/work-log.csv`, or `python3 tools/log_piece.py
   my-log.jsonl`). The line is written when the piece closes, and `check` names the check that decided
   acceptance: step 4, or a hidden test or a qualified reviewer. Steps 1 and 3 leave no field of their
   own. The steps you used may go in the optional `tools` field (for example "list, fresh review,
   other family"); `horizon.py` does not read it and scores the piece by the same rules as any other.
2. Keep the acceptance card with its list, and the verdict of step 4, next to the log line.
3. When a piece carries planted errors, sealed by someone else (`planted-errors-guide.md`),
   `python3 tools/planted.py score` gives its log line `planted_errors` and `planted_missed` and shows
   what was missed, wrong entries and omissions apart. The auditor's outcome file can also say which
   step caught each error, in a `caught_by` column: `list` (step 1), `fresh_review` (step 3),
   `other_family` (step 4), `own_reading`, `own_test` (a test or reconciliation you ran) or `other`.
   Kept across pieces, it shows which step catches which kind; the column changes no rung.

Three lines from one newcomer's log in bookkeeping, each valid for `horizon.py` (every field of
Appendix C1, with `started`):

```json
{"person": "P12", "domain": "small-business bookkeeping", "started": "2026-10-01", "date": "2026-10-02", "reference_hours": 8, "reference_basis": "two raters", "attention_minutes": 150, "mode": "stages", "check": "other_family_with_sources", "agent_saw_check": false, "passed": true, "irreversible": false, "planted_errors": 2, "planted_missed": 0, "outside_help": false, "model": "agent and reviewer: family A; check: family B", "checker": "model of another family, against the bank statements and bills the person opened"}
{"person": "P12", "domain": "small-business bookkeeping", "started": "2026-10-05", "date": "2026-10-05", "reference_hours": 3, "reference_basis": "two raters", "attention_minutes": 40, "mode": "one_piece", "check": "same_family", "agent_saw_check": false, "passed": true, "irreversible": false, "planted_errors": 0, "planted_missed": 0, "outside_help": false, "model": "agent and reviewer: family A", "checker": "model of the agent's family, in a fresh context"}
{"person": "P12", "domain": "small-business bookkeeping", "started": "2026-10-07", "date": "2026-10-08", "reference_hours": 2, "reference_basis": "two raters", "attention_minutes": 70, "mode": "one_piece", "check": "expert", "agent_saw_check": false, "passed": true, "irreversible": true, "planted_errors": 0, "planted_missed": 0, "outside_help": false, "model": "agent and reviewer: family A; second line: family B", "checker": "qualified bookkeeper; second line: model of another family, against the approved invoices"}
```

- Line 1 is verified. A month-end close, which can be corrected, checked by a model of another family
  against the bank statements and bills the person opened; both planted errors, a wrong entry and an
  omission, were caught.
- Line 2 is not verified. The person accepted an accruals schedule on the fresh reviewer's word alone,
  and `same_family` earns no credit, whatever the review found.
- Line 3 is verified. A file of supplier payments, where money once moved cannot be called back, was
  checked by a qualified bookkeeper before release, with another family as a second line. Had the
  other family been the only check, `horizon.verified` would return false for this piece.

## What the process cannot see

- **Omissions not on the list.** Models are far worse at noticing what is missing than at finding what
  is there, even with the original beside them (Fu et al., 2025), so an item the list does not name is
  shown to no reviewer. Put omissions among the planted errors (`planted-errors-guide.md`), so an
  incomplete list shows in the record.
- **Correlated errors across models.** Larger and more accurate models make highly correlated errors
  even across providers (Kim et al., 2025), so a second family is a better guess at independence than
  a second model of the same family, not a measurement of it (Chernets, 2026b). Keep an independent
  check: a hidden test, a qualified reviewer or real use.
- **Warnings that do not make a checker.** Professionals told repeatedly that an AI makes mistakes
  still missed critical flaws in its analysis (Virk and Liu, 2025). Ask for the work laid out as
  explicit steps, with the alternatives at each decision, which helped in that study, and keep the
  independent check.
- **A figure that agrees.** A balance that agrees is no proof. In one accounting-software maker's
  benchmark of 2025, models asked to close a company's books month by month either gave up within the
  first month or accumulated errors, and when their figures did not match the bank balance some pulled
  in unrelated transactions to make them agree (Penrose, 2025, as reported by Gigazine, 2025). Check
  each figure against its source, not only the total.

## How to make the list name what is missing

1. Ask each model on its own, in the same words, three questions: what must this deliverable contain,
   what do people in this trade most often leave out of it, and which checks apply to it.
2. Merge the answers into one list. Keep every item that any model named, and remove only duplicates.
3. Write each item as a question with a yes or no answer and the place to look, for example: "Is every
   bill received after the period end for services within the period accrued? Compare the bills
   folder with the accruals schedule."
4. Check the result item by item against the sources, the list first and the reading second. Model
   judges that first listed the facts a source established and then checked a note for each found
   omissions better, though they still flagged only 25% to 37% of the notes that had one (Fox et al.,
   2026).
5. Put the list into the statement of done before the hand-over (`acceptance-card.md`), so that it is
   dated and cannot be fitted to the result.
6. Test the list with planted omissions. A colleague or an auditor removes from the task material
   something the work must contain (a known bill, a mandatory clause) and seals the record of what was
   removed (`planted-errors-guide.md`, `python3 tools/planted.py seal`); the log records
   `planted_errors` and `planted_missed`. An omission the list does not name shows up as a miss, and
   the missed item joins the list for the next piece.
