# Delegation horizon

Companion code for the paper **"After the Programmer Divide: One Measure for People Who Build Through AI Agents"**
(Vadym Chernets, October 2026). It turns a log of work handed to AI agents into two numbers and one dated record:

```
small-business bookkeeping · Day · ×2 · 2026-Q4
```

That line reads: in small-business bookkeeping, this person regularly hands agents pieces of work that would take a
specialist about a day by hand, and an independent check the agents did not see confirms them (the **verified
delegation horizon**); for every hour of their own attention they get at least two hours of verified work (the
**amplification gain**); scored in the fourth quarter of 2026.

| | |
|---|---|
| **Paper, version of record** | [SSRN 7589918](https://ssrn.com/abstract=7589918) · DOI [10.2139/ssrn.7589918](https://doi.org/10.2139/ssrn.7589918) |
| **Paper, archived** | [10.5281/zenodo.23267267](https://doi.org/10.5281/zenodo.23267267) |
| **Paper, full text on GitHub** | [vadimchernets/papers/after-the-programmer-divide](https://github.com/vadimchernets/papers/tree/main/after-the-programmer-divide) |
| **Predictions, registered on OSF** | [10.17605/OSF.IO/VW6P9](https://doi.org/10.17605/OSF.IO/VW6P9) |
| **This code, archived** | [10.5281/zenodo.23267444](https://doi.org/10.5281/zenodo.23267444) |
| **Tests** | `python3 -m unittest discover -v`, run on every push for Python 3.9 to 3.13 |

Python 3.9 or later, standard library only. No accounts, no keys, no network: everything runs on your own computer
and your log never leaves it.

## Five minutes, no programming

1. Open `templates/work-log.csv` in any spreadsheet (Excel, Numbers, LibreOffice, Google Sheets).
2. Add one row for each piece of work you handed to agents and closed: accepted, rejected or abandoned. Keep the
   failures. `templates/README.md` explains every column in plain words; `examples/c4-log.csv` is a filled-in log
   of ten rows to copy from.
3. Save it as CSV, for example as `my-log.csv` in this folder.
4. Open a terminal in this folder and run

   ```sh
   python3 record_card.py my-log.csv
   ```

You get the record line and a card: the rung, the gain, how many pieces were verified and how many were not, which
kinds of check were used, the median verified size. Add `--format md --out card.md` for a card to paste into a
profile or send to an employer, or `--format record` for the single line a resume needs. Add `--as-of 2026-12-31`
to score on another date.

No terminal at all? Open `checker.html` in a browser (double-click it), choose your CSV or JSON Lines log, and you
get the same record and counts as `horizon.py`, with the same rules; the file never leaves your computer and the
page needs no network. A test runs the page's scorer against `horizon.py` on the worked example and on 40 random
logs. `python3 tools/log_piece.py my-log.jsonl` writes log lines by asking questions instead.

Try it on the worked example first:

```sh
python3 record_card.py examples/c4-log.csv --as-of 2026-10-09
```

### What counts (rules v1.1)

| Rung | Size of one piece | Pieces needed | Window |
|---|---|---|---|
| Hour | 1 reference hour | 10 | 91 days |
| Day | 8 | 10 | 91 days |
| Week | 40 | 6, at least one with planted errors | 182 days |
| Month | 160 | 6, at least one with planted errors | 365 days |
| Quarter | 500 | 3, at least one with planted errors | 365 days |

At least eight of every ten pieces must pass a check of one of four kinds: hidden tests, a qualified expert, real
use by the intended users, or a model of another family that checked against sources you opened. Every piece whose
mistakes cannot be undone must pass, and for such a piece another model family is never the only check. From Week
upward, one piece must have fallen within the last 91 days, and a single planted error you missed blocks Week and
above for the window. A piece someone helped with off the log counts as an attempt and never as a pass; so does a
piece whose audit failed or whose result was later revoked. Gain is verified reference hours divided by all your
hours of attention in the last 91 days, failures included. The steps are ×1, ×2, ×5, ×20 and ×60. The full rules,
and why each exists, are in Section 5 of the paper; `CHANGELOG.md` lists what changed in v1.1 and why.

`horizon.py` prints the count next to the rung, `Day (8/10)` (verified pieces of the rung's size out of all such
pieces in its window), the kinds of check behind them and the median accepted size, so a record that only just
holds, or tasks chosen just above a threshold, show at once. `--stable` also scores the date 91 days earlier and
labels the rung `stable` or `provisional`.

## What this score means, and what it does not

A record such as `financial tools · Week · ×2 · 2026-Q4` says three things and no more:

- **What was verified.** In that domain, in the last 182 days, at least six pieces of about a week of specialist
  work each were handed to agents, at least eight in ten passed a check the agents never saw, every irreversible
  one passed, planted errors were caught, and one such piece is from the last 91 days.
- **At what cost in attention.** Every hour the person spent planning, reading, checking and fixing bought at least
  two hours of verified work, with the failures counted against them.
- **When.** The quarter of scoring. A rung is confirmed again every quarter; an old record is a dated fact, not a
  standing title.

It does not say how the person would do in another domain, how well they code, how fast they type prompts, how many
tokens they spend, or whether they hold a degree. It does not rank people inside a rung, and it is not a licence for
work whose mistakes harm others: that still needs whatever qualification the work has always needed.

## How to audit a record

Ask for the log behind the record; the card says it is available on request. Then:

1. **Rescore it.** `python3 horizon.py their-log.jsonl --as-of <date on the card>` must print the same line. A card
   written with `--format json` carries the SHA-256 of the log and of the scorer, so a different log or a changed
   scorer shows at once.
2. **Draw a sample for a second check.** `python3 audit_sample.py their-log.jsonl --as-of <date>` draws a
   reproducible random share of accepted pieces (seed printed; the default seed is the date), at least one per person
   and domain; `--all-irreversible` adds every irreversible piece. Give the sample to a checker who did not see the
   first check.
3. **Read the pattern, not only the result.** A log with no failures, identical sizes, or every check of one kind is
   a reason to look closer (Table 3 of the paper lists the ways the measure can be gamed and the defence for each).
   A rung with `self_review`, `same_family` or `none` behind it is not a rung, and the scorer does not count those.
4. **Check the reference hours.** They must come from a named task bank or from two raters blind to the person; the
   field `reference_basis` says which.

## For an organisation

- **Keep one log per team.** One row per piece, one pseudonymous label per person (the scorer refuses unknown
  fields, so real names cannot slip in as an extra column). Each person logs their own attention; a piece accepted
  together counts for the person who signed the acceptance. `examples/team-log.csv` is a team of four across five
  domains: one person at Week, a missed planted error that holds another at Day, and a failed irreversible piece
  that blocks every rung it reaches.
- **Fix the reference hours outside the team.** Either build a task bank with `templates/task-card.md` (what counts
  as done, measured by-hand time, hidden checks, planted errors) or have two raters, blind to the person, estimate
  each deliverable. A disagreement above a fixed ratio between the two sends the piece to a third rater (the
  paper's pilot targets a ratio within 1.5).
- **Keep the checks hidden and independent.** Whoever runs a check gains nothing from a pass; the agents never see
  it. Re-check a random share of accepted pieces every quarter with `audit_sample.py`.
- **Plant errors from Week upward.** The task card has a field for them. A miss is recorded, never quietly fixed.
- **Score every quarter.** `python3 record_card.py team-log.csv --format md --out cards.md` prints a card per person
  and domain; `--person P07` prints one. A rung is per domain: the same person can be at Week in financial tools and
  at Day in web applications, as P01 in the team example is.
- **Move records between systems** with `--format json`: one portable record per line, described by
  `export-record.schema.json`, for a hiring platform, an HR file or a research database.

For researchers the JSON Lines format of Appendix C1 is the primary one: `log.schema.json` describes it, and
`horizon.py` reads it directly. `python3 record_card.py team-log.csv --to-jsonl team-log.jsonl` converts a
spreadsheet log.

## Paper section to tool

| Paper | File | What it does |
|---|---|---|
| 5.2, C2 | `horizon.py` | Scores the horizon and the gain from a JSON Lines log, rules v1.1. Byte for byte as printed in the paper |
| C1 | `log.schema.json` | JSON Schema of one log line |
| C4 | `examples/c4-log.jsonl`, `c4-log.csv`, `c4-expected.txt` | The worked example and the lines it must print |
| 5.2 | `examples/team-log.jsonl`, `team-log.csv`, `team-expected.txt` | A team of four, five domains, Week and planted errors, and the lines it must print |
| 5.3 | `record_card.py` | Reads a JSON or spreadsheet log and prints the record and a card (text, Markdown or portable JSON), using `horizon.py` unchanged |
| 5 | `checker.html` | The same scoring in a browser page, offline, for people who do not use a terminal |
| 5.2 | `tools/log_piece.py`, `integrations/claude-code-hook/`, `kits/acceptance-card.md` | Writing the log: questions instead of JSON, an entry opened after every agent session so failures are not lost, and a card that states "done" before the hand-over |
| 10.3 | `export-record.schema.json` | Portable record format, with hashes of the log and the scorer |
| 5.8, Table 3 | `audit_sample.py`, `tools/too_clean.py`, `kits/audit-checklist.md`, `kits/planted-errors-guide.md` | Reproducible audit sample; flags for logs that look too clean; audit checklist; how to prepare and seal planted errors |
| 5.8, App. E | `pilot/` | Desk pre-pilot of the thresholds (simulated logs, exact rates, rater noise), a 30-task bank, and the protocol, preregistration draft and consent form of the live pilot |
| 5.1, 7.2 | `templates/` | Spreadsheet log, task card for a task bank, guarantor record |
| 3, 4, 6 to 13 | `kits/`, `tools/` | One kit or tool per section: names, tokens in reviews, matched-task study, degree share of postings, guarantor sign-off and product liveness, release checklist by risk, codebook and kappa, a one-day hiring test, pre-release security scan, scope statement. The map is `kits/README.md` |
| 1, 2, 13 | `sources/` | Register of claims with archived copies, refreshed monthly by a workflow |
| 11, Table A6 | `predictions/` | The dated predictions (registered on OSF, DOI 10.17605/OSF.IO/VW6P9), resolution rules, files for resolving specific predictions, and the scorecard tools |
| C3 | `brier.py` | Brier score over dated predictions. Byte for byte as printed in the paper |
| | `tests/` | `python3 -m unittest discover -v` |

Check the worked example yourself:

```sh
python3 horizon.py examples/c4-log.jsonl --as-of 2026-10-09
```

## Scoring the predictions

**The prediction table is registered on OSF on 9 October 2026, DOI 10.17605/OSF.IO/VW6P9 (https://osf.io/vw6p9), and frozen.** Its probabilities were
fixed on 9 October 2026 as the median of three blind model forecasts, adopted by the author (predictions/changelog-v1-v2.md); the history of every change stays in git. After registration the
table is never edited: a new prediction is registered separately and carries its own date.

Copy `predictions/outcomes-template.csv` to `outcomes-2027.csv`, set each status to `came_true`, `did_not`,
`not_yet_due` or `unresolved`, write the evidence, and run

```sh
python3 predictions/score.py outcomes-2027.csv
```

The probabilities are read from the frozen table, never from your file. Every prediction must appear; an
unresolved one is never counted as a success. A forecast at 35% that misses says little on its own: the Brier
score over the set is what tells a calibrated forecaster from a lucky one (always saying 0.5 gives 0.250).
`python3 predictions/skill.py outcomes-2027.csv` adds the rest of Section 11.4: scores by set and by family of
linked predictions, the share resolved, a worst bound that counts every overdue unresolved prediction as wrong,
and the skill score against a flat 0.5, the pooled model forecasters and market prices where they exist. The rules
are in `predictions/resolution-rules.md`; `predictions/changelog-v1-v2.md` says what changed in the table and why.

## Scope

The scorer trusts the fields it is given. It does not judge whether a check was well chosen, whether reference
hours are fair, or whether a check was independent beyond its kind and whether the agents saw it; independence is
confirmed by audit. The thresholds are provisional: they were desk-tested without people (Appendix E of the paper) and await the pilot with people; until
the human pilot reports, the record is a research measure, not a basis on its own for hiring, pay or certification
decisions. A card is a summary of a log: the log is the evidence.

## What is deliberately not here

No lesson plans, curricula, level diagnostics or routing of learners: the paper's ideas of a course built around the
measure (Section 10.2) and a one-question onboarding check (Section 10.4) are described there in prose only. This
repository holds research instruments, not teaching materials.

## Licence and citation

MIT (see `LICENSE`). Please cite the paper (see `CITATION.cff`). This is independent work, not affiliated with or
endorsed by any maker of AI agents. The author develops multi-model orchestration methods and has filed related
patent applications (pending; no patent has been granted).
