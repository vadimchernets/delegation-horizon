# Protocol: feasibility pilot of the verified delegation horizon

Version 0.1, 9 October 2026. Ready for registration; not yet registered. The desk pre-pilot
(`README.md`, Appendix E of the paper) fixed the questions this pilot must answer and the rule changes
of v1.1 that it tests.

## 1. Questions and pre-set criteria

| Question | Measure | Criterion fixed in advance |
|---|---|---|
| Q1. Do two blind human raters agree on reference hours? | Share of pieces whose two estimates lie within x1.5; ICC(2,1) on log hours | At least 70% of pairs within x1.5 (target of the paper: 80%) |
| Q2. Are rated hours close to measured hours? | On the measured share of tasks: share of rated values within x1.5 of the measured by-hand time | At least 60% within x1.5, median ratio between 0.67 and 1.5 |
| Q3. Is a person's rung repeatable? | Agreement of the rung in two consecutive 91-day windows (weighted kappa over the ordered rungs) | Kappa at least 0.6 |
| Q4. Does the rung predict new work? | Pass on three new bank tasks at the rung's size and one rung above, after the second window | AUC at least 0.7 for passing at a rung given the rung held |
| Q5. Is the protocol feasible? | Lost log lines; failed or abandoned hand-overs recorded; drop-out | Fewer than 5% lost lines; at least 95% of failed hand-overs recorded; drop-out under 25% |

A criterion that is missed is reported as missed, with the threshold that would have passed. Thresholds
of the rules (counts, share, windows) are changed only after the pilot and only in a new version.

## 2. Participants

- 60 adults: 30 with a degree or job history in software, 30 without. A larger run of 100 is allowed
  if recruitment allows; two domains instead of three if the bank is not ready.
- Recruited openly. No cohort, class or course data are used, and no existing consent is reused.
- Pseudonymous labels only (`P01`...). Each person works in one or two of the three domains.

## 3. Domains and tasks

- Three low-risk domains: small-business bookkeeping on synthetic books; small internal web tools;
  legal and marketing documents on synthetic material. No real client data, no irreversible work.
- Tasks: the bank grows from v0 (30 tasks, `task-bank-v0.md`) to at least 60 per domain before
  start, covering Hour, Day and Week. Month and Quarter are out of scope for a 6-month pilot and are
  reported as such.
- Each task has a statement of done, a hidden check the agents cannot see, and planted errors from
  Week up. Participants may also log their own work; such pieces are rated by two raters.

## 4. Reference hours

- On 20% of bank tasks, by-hand time is measured: a qualified specialist does the task without agents
  under observation, timed. These are the anchors for Q2.
- Every task and every own-work piece gets two blind estimates from qualified specialists of the
  domain, who do not know who did the work. If the ratio exceeds 1.5, a third rater decides (Table 3).
- Before rating, raters calibrate on five anchor tasks with measured times and see their error.
  Reason from the desk pre-pilot: uncalibrated model raters differed by a factor of two in their
  overall level, and a stable level offset is the cheapest error to remove.
- Model raters of other families are recorded in parallel as a secondary comparison, never as the
  reference.

## 5. Agents, checks and logging

- The same agent tools for all participants, versions frozen for each window and logged (`model`, `tools`).
- Checks: hidden tests for web tools; two blind domain reviewers for bookkeeping and documents. The
  reviewer is recorded as a role in `checker`.
- Every hand-over is a line of `log.schema.json` v1.1 with `started`, written when the piece closes,
  including failed and abandoned pieces. A random 10% of accepted pieces gets a second independent
  audit (`audit`).
- Attention minutes are logged per piece by a timer in the work environment, not from memory.

## 6. Schedule

| Weeks | Step |
|---|---|
| 0-4 | Registration, ethics review, bank to 60 tasks per domain, measured anchors, rater calibration |
| 5-17 | Window 1 (91 days) |
| 18-30 | Window 2 (91 days) |
| 31-32 | Prediction tasks (Q4), analysis by the registered plan |

## 7. Analysis

Scored by `horizon.py` v1.1 with `--stable`. Q1 and Q2 by `pilot/rater_agreement.py` on human ratings.
Q3 by weighted kappa; Q4 by AUC with 95% bootstrap intervals; sensitivity of every result to the count
(8, 10, 12) and share (0.7, 0.8, 0.9) by re-scoring the same logs, as in `pilot/simulate_rules.py`.
Programmers and non-programmers are compared on rung and gain (hypothesis F7 of the paper) as an
exploratory outcome only; the pilot is not powered for it.

## 8. What the pilot will not settle

The upper rungs (Month, Quarter); irreversible work; domains with high risk; whether the rung predicts
pay or hiring. These need longer and larger studies.
