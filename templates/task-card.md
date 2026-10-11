# Task card

One card per task in a frozen task bank (Section 5.1 of the paper). A bank holds, for each domain, tasks at every
rung. Keep the hidden part of the card away from the person and from the agents: a check the agents could see does
not count.

## Public part (given to the person)

| Field | Value |
|---|---|
| Task id | |
| Domain | |
| Rung it is built for | Hour / Day / Week / Month / Quarter |
| Version and freeze date | |
| The task, as handed over | |
| Inputs supplied | (files, data, access; all inputs must be ones the agents did not produce) |
| What counts as done | (a written statement a stranger could check: deliverable, format, acceptance criteria) |
| Irreversible? | yes / no (if yes, every such piece must pass) |

## Reference time (kept with the bank)

| Field | Value |
|---|---|
| Measured by-hand time | (hours, for the whole deliverable as accepted) |
| How it was measured | (timed specialists, number of them, date; or two blind raters and their two estimates) |
| Specialists' qualification | |
| Spread between measurements | (ratio of the highest to the lowest; above the fixed ratio, a third rater; the paper's pilot targets 1.5) |
| Review time | (measured minutes a qualified reviewer needs to check a deliverable) |

## Hidden part (never shown to the person or the agents)

| Field | Value |
|---|---|
| Hidden checks | (tests, a reviewer's checklist, or the real-use signal that decides acceptance) |
| Who runs the check | (must gain nothing from a pass) |
| Planted errors | (each error, its kind, where it sits in the inputs or what they leave out, and what catching it looks like; required from Week upward, and from Week upward at least one should be an omission wherever the work has something it must contain; the list as in `kits/planted-errors-guide.md`) |
| Kind of each planted error | wrong entry (something in the material is wrong) / omission (something the work must contain is missing) |
| SHA-256 of the sealed list | (from `python3 tools/planted.py seal`, written here before the hand-over) |
| How a miss is recorded | (any missed planted error makes the piece unverified and blocks Week and above in the window) |
| Delayed outcome | (what to record later, and when: a filing accepted, a release still running after a month) |

## Audit trail

| Date | Change | By |
|---|---|---|
| | Card frozen | |
