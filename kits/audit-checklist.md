# Audit checklist for a delegation record

*Paper: Section 5.8 and Table 3 (ways to game the measure, and the defences).*
*For: organisations, auditors and guarantors who need to trust someone else's record.*

Pick a random share of accepted pieces (for example one in five; `audit_sample.py` draws it with a
seed you can publish) and go through this list for each one. Run `tools/too_clean.py` on the whole log
first: it tells you where to look.

## A. The check itself (route: easy checks)
- [ ] The check was fixed before the hand-over (dated acceptance card or task record).
- [ ] The agents could not see it: hidden tests outside the agents' workspace, a reviewer the agents
      never addressed, real users, or a different model family working from sources the person opened.
- [ ] A second independent checker, re-running the check now, gets the same verdict.
- [ ] For Week-size pieces and above: planted errors exist, were sealed before hand-over, and were caught.

## B. The size (routes: thresholds, generous raters, slicing)
- [ ] Reference hours come from a named task bank or from two raters blind to the person.
- [ ] If two raters differ by more than the agreed ratio, a third rater or the frozen bank decided.
- [ ] The piece is one coherent deliverable accepted as a whole, not a slice of a larger one.
- [ ] Sizes are not bunched just above a rung threshold (8.1 hours for Day, 41 for Week).
- [ ] The median accepted size is reported next to the rung.

## C. The person (routes: hidden help, parallel streams)
- [ ] Attention minutes are plausible for the piece; a short replay or interview confirms the person
      can explain the work and the check.
- [ ] Outside help is recorded as such and excluded from gain.
- [ ] Attention in parallel streams is counted once per person-minute.

## D. The log (route: hiding failures)
- [ ] Every hand-over has a start date and was closed as accepted, rejected or abandoned.
- [ ] Failures exist in proportion to the work; a long log with none is examined, not praised.
- [ ] Pieces that passed but were later found wrong were recorded as failed and the rung rescored.

## E. Result
| Outcome | Action |
|---|---|
| All items hold | Record stands; note the audit date next to it |
| One piece fails audit | Mark it failed in the log, rescore with `horizon.py` |
| Systematic problem | Record withdrawn until a new window is logged |

Keep the audit sheet with the record. An audited rung is worth more than a self-reported one.
