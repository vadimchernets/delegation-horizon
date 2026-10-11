# Process or experience: a 2 x 2 study protocol

*Paper: Section 10.5 (for researchers) and Section 6.5 (newcomers to a trade who check by process).*
*For: researchers, and organisations that want to know how much of a trade's experience a checking process can stand in for.*

Section 6.5 asks whether a newcomer to a trade who works by a checking process can deliver work that
passes more independent checks than an experienced professional who accepts one agent's output as it
comes. Section 10.5 sets out the comparison that would show how much of a trade's experience a process
can stand in for, and at which rung that stops. This file is that comparison as a protocol to adapt and
register. Section 10.5 notes that it is not among the registered predictions of Section 11, which are
frozen: it is registered on its own, before data are collected.

## Design
| Element | Rule |
|---|---|
| Arms | Experience in the trade (present or absent) crossed with the way of working (one agent, or the checking process): four arms. The way of working is assigned at random within each experience group, after the screen is scored |
| Experience | Established by a knowledge screen and a record of work, not by a profile label (Section 6.2 explains why). Present: a record of work in the trade (job history; the registration sets the minimum) and a passed screen. Absent: neither training nor work in the trade. People who fit neither are not enrolled, and their number is reported |
| Knowledge screen | Questions of the trade, scored before assignment (`trade-screen.md`). Everyone takes it. Run it supervised or under a strict time limit, since chat models answer static screening questions (Section 6.2) |
| One agent | The person gives the task to one agent and accepts or rejects its output as it comes, on their own reading: no list from models, no second model |
| Checking process | The four steps of `checking-process.md`: a must-contain list from several models before the work, one agent, a review in a fresh context, and a model of another family checking against sources the person opened |
| Tasks | The same tasks in every arm, from a frozen bank (Section 5.1), at Day and Week size, each with a written statement of done, in one named domain at a time |
| Agents and budget | The same working agent, models, settings, time and budget in every arm; versions logged in `model` and `tools` |
| Checks | Checks the agents did not see: hidden tests or qualified reviewers blind to the arm. Pieces whose errors cannot be undone are checked by a hidden test or a qualified human (Section 5.2). The person's own steps are part of the way of working, never the study's check |
| Planted errors | On every piece from Day size up, both kinds: wrong entries and omissions, each sealed with its kind (`planted-errors-guide.md`) |
| Logging | Every piece in the work log of Appendix C1, failed and abandoned ones included |

## Outcomes, at Day and at Week separately
| Outcome | Definition |
|---|---|
| Verified pass share | Pieces verified by the rule of Section 5.2 (the study's check passed, no planted error missed), over all pieces handed over |
| Omissions caught | Planted omissions caught, over omissions planted |
| Wrong entries caught | Planted wrong entries caught, over wrong entries planted; never pooled with omissions (Section 10.5) |

## Analysis plan (register it before data)
`tools/process_study.py` makes the analysis. For each outcome it prints the four cells with Wilson 95%
intervals; the process effect among newcomers, the experience effect under one agent and their
interaction, each with a 95% interval from a bootstrap that resamples people within each cell; and the
share of the experience gap the process closes.

1. Primary: the interaction on the verified pass share, at Day and at Week. The tool prints it as the
   process effect among the experienced minus the process effect among newcomers, so a negative value
   means the process closes more of the gap for people without experience.
2. With it, the main effects of experience and of the way of working, each averaged over the other
   factor, from the same four cells.
3. Secondary: the same for omissions caught and for wrong entries caught, apart. The list drawn up
   before the work is aimed at omissions and the reviewers at wrong entries (Section 10.5).
4. The share of the experience gap the process closes (the process effect among newcomers over the
   experience effect under one agent) answers the question of Section 6.5: above 100%, newcomers with
   the process did better than experienced people who accept one agent's output as it comes. The tool
   prints it only when the interval of the experience effect lies above zero.
5. Report every participant, including those who failed the screen or dropped out, and every task,
   including failures.

Section 6.5 states what the rival of Section 6.1 (Savva, 2026) expects: the process doing best on
short, well-specified tasks and worst at the upper rungs, and experienced people who adopt it doing
better than either group. The interaction at Day against Week tests the first; the arm of experienced
people with the process tests the second.

## Size
`--power` gives the number per cell needed to tell two cells apart (normal approximation, two-sided
alpha 0.05), with a design effect when each person gives several observations. One worked example:

```
$ python3 tools/process_study.py --power 0.50 0.65 --per-person 4 --icc 0.2
two proportions 0.5 and 0.65; two-sided test at 0.05; normal approximation without continuity correction
n counts observations per cell: planted errors of one kind, or pieces
n per cell for 0.80 power: 170 (680 in the four cells)
design effect 1.60 (4 observations per person, correlation 0.2 within a person):
  n per cell for 0.80 power: 68 people, 272 observations per cell (272 people in the four cells)
```

Here 0.50 and 0.65 are the verified pass shares you expect from newcomers with one agent and with the
process; each person hands over four pieces of the size, and two results of one person are assumed to
correlate at 0.2. Change the two shares to your own expectations (from a pilot, or past data on the same
bank), `--per-person` to the number of pieces (or planted errors of one kind) each person gives, and
`--icc` to your estimate. The interaction is a difference of two such differences and has twice the
variance: an interaction as large as the difference between two cells needs about twice the number per
cell, and one half as large about eight times. Size Day and Week separately.

## Data files
| File | One row per | Columns |
|---|---|---|
| Work log (JSON Lines or `templates/work-log.csv`), scored by `horizon.py` | piece | Appendix C1, with `task_id` |
| Planted errors | planted error | `participant`, `experience` (`present` or `absent`), `way` (`one_agent` or `process`), `rung`, `kind` (`wrong_entry` or `omission`), `caught` (1 or 0); optionally `caught_by` (`planted-errors-guide.md`), which the tool ignores |
| Pieces | piece | `participant`, `experience`, `way`, `rung`, `verified` (1 or 0, as `horizon.verified` returns it for the piece's log line) |
| Screen sheet | person | `person`, `screen_score`, `passed` (yes or no); `experience` and `way` are added at assignment |

`participant` is the pseudonymous label used as `person` in the log. Each piece's planted errors are
sealed and scored with `tools/planted.py` (`planted-errors-guide.md`), which also gives its log line
`planted_errors` and `planted_missed`. Then

```sh
python3 tools/process_study.py errors.csv --pieces pieces.csv --by-rung
```

prints every block for all rungs together and for each rung, with the seed of the bootstrap, so the
result can be reproduced.

## Practical notes
- Every arm works through the same agents: a comparison with professionals who work without agents
  would settle nothing here (Section 11.1).
- Keep the must-contain list of every piece in the process arm, so an omission caught by `list` can be
  traced to the list that named it.
- Publish the task bank hash, the reference hours and the analysis code before results.
