# Changelog

## 1.1.0 (2026-10-11, not yet released)

The rules v1.1 are unchanged. `horizon.py` changes in two places, and Appendix C2 of the paper prints the new listing
(`tools/paper_sync.py` and `tests/test_instrument.py` check it byte for byte): the gain adds hours and minutes with
`math.fsum`, so a gain that lands on a step edge prints the same on Python 3.9 to 3.14 (built-in `sum` adds floats
differently from 3.12 on), and `checker.html` adds the same way; "needs third rater" is printed only for a piece with
two estimates more than 1.5 apart, not once the third estimate is in. `brier.py` is unchanged.

Fixes after the independent review of 10 October 2026:
- F27 sample (`tools/freeze_sample.py`, `kits/f27-sample.md`): commit, then reveal. A seed published before
  collection let a collector compute every key and choose which products to enter. Now `--digest` prints the SHA-256
  of the closed pool, which is registered on OSF, and the key is a public drand beacon round published after that
  registration (`--beacon`); one spelling per product (GitHub owner/repository only; https:// added), written so into
  the frozen file; dates read by one rule on every Python; the sample's hash is registered on OSF with the Zenodo
  DOI by 31 December 2026, since a Zenodo record's files can be changed for 30 days.
- `tools/liveness.py` follows F27's registered words, "unreachable or not updated for 12 months": archived is its
  own column and does not retire a product; 403, 429 and 5xx are retried and, if they persist, marked unknown for
  the hand check instead of retired; GitHub's rate limit is waited out from its reset header, and an optional
  `GITHUB_TOKEN` raises it; GitHub addresses are recognised in any spelling; an address without a scheme no longer
  stops the run; `checked` is the day of the run and `as_of` its own column, and a push after `as_of` goes to the
  hand check; the summary gives the retired share with one decimal.
- `audit_sample.py`: the seed comes from the SHA-256 of the closed log, the date and `--salt`, a word the second
  checker picks after receiving the log, so the person logging cannot know which lines will be drawn.
- `tools/guarantor_record.py` counts status and failures as they stood on `--as-of` (optional `failed_on`).
- `tools/name_race.py` counts every candidate of Table A2 (`tools/names-table-a2.txt`) by default.
- Figure A1: F32 is labelled in the registered changelog's words ("Vendor reports non-developer majority"), the
  RevenueCat bar as the table names it ("2027 report"), and F34's protocol deadline is drawn over its check dot.
- `.gitattributes` keeps every file byte for byte on every system, so the hash checks pass on a Windows clone.

- The predictions are registered (OSF, 9 October 2026, DOI 10.17605/OSF.IO/VW6P9): `score.py` prints the
  registration instead of "DRAFT, not yet registered", and the READMEs say so. `predictions/registered-SHA256.txt` is
  the manifest filed with the registration, copied unchanged; `tests/test_registered.py` checks that every registered
  file here is still the one registered, and that the three files filed with the Prolific pre-pilot (OSF
  10.17605/OSF.IO/V92R8; `pilot/registered-SHA256.txt`) are unchanged.
- `checker.html` reads a CSV saved from `templates/work-log.csv` with its optional columns left empty (it stopped at
  "outside_help and revoked must be true or false"), and reads `revoked` and `rater_hours`. It and `record_card.py`
  read a spreadsheet saved with semicolons, decimal commas and day.month.year dates, and name an unreadable date
  (such as 9/14/2026) with its row instead of failing.
- `record_card.py`: the card prints the count behind the rung ("8 of 10 pieces of Day size verified in its 91-day
  window (8 needed)"), as `horizon.py` does.
- `tools/explain.py` (new): why a log earns its rung, condition by condition, with the deciding pieces, the slack,
  the day the rung lapses if nothing new is logged, what the next rung needs, and the exact interval of the pass
  rate the count fits. A test ties its conditions to `horizon.rung_holds` on random logs.
- `tools/planted.py` (new): seals a planted-error list by hash before the hand-over and scores it by kind after,
  wrong entries and omissions apart, refusing a list changed after sealing. `kits/planted-errors-guide.md`,
  `templates/task-card.md` and `kits/hiring-test/hidden-check.md` add the omission as a kind of planted error
  (Appendix A, Sections 6.5 and 10.5).
- `tools/reference_hours.py` (new) and `kits/reference-hours-raters.md` (new): reference hours from two raters'
  estimates (geometric mean within 1.5, otherwise a third rater), and how to choose, admit and brief raters.
  `kits/hiring-test/README.md` used "the mean if they agree within a third"; it now follows the paper's rule.
- `tools/power.py` (new): power and sample size for two pass shares; it reproduces Section 11.2 (1,500 per group,
  about 0.8 power for 5 points; 400 per group, about 0.3).
- `tools/too_clean.py` adds the two traces the README promised and the tool lacked: sizes that barely vary, and
  every piece checked by one kind of check.
- `templates/README.md`: the question for `irreversible` was reversed ("can a mistake here be undone?"); it now asks
  whether a mistake would be impossible to undo. The seven optional columns are explained.
- `pilot/`: `prolific_to_long.py` reads each estimate as written (".5" was read as 5, "1,200" as 1.2 and "8-12" as 8)
  and lists every answer that is not a plain number; the table of Appendix G2 and the comparison of its screening
  get their own scripts, and `demo/` holds two synthetic exports to run them on. The README no longer says that no
  people took part in anything in the folder.
- `figures/figure_a4_checking_process.py` (new): draws Figure A4 of the paper, reading the credit of each kind of
  check from `horizon.py`.
- `tools/gate_leak.py` and `kits/trade-screen.md` (new, Section 6.2): admit people by a question of the trade instead
  of a label, and report how much a label leaks with an exact (Clopper-Pearson) interval; 11 of 60 gives 18.3%
  (9.5% to 30.4%).
- `kits/checking-process.md` (new, Section 6.5): the four steps, what each earns in the log, three example log lines
  that the tests score with `horizon.py`, and how to make the must-contain list name what is missing.
- `kits/process-vs-experience-study.md` and `tools/process_study.py` (new, Section 10.5): the 2 by 2 comparison as a
  protocol to register, and its analysis: wrong entries and omissions scored apart, Wilson intervals per arm, a
  bootstrap over people for the two effects and their interaction, and `--power` for the cells.
- `predictions/set_b.py` (new): the frozen came-true and did-not rules of the nine Set B predictions written on an
  interval, applied to a study's estimates.
- `kits/f27-sample.md` and `tools/freeze_sample.py` (new): F27 is unresolved unless its sample of at least 300
  agent-built products is frozen on Zenodo by 31 December 2026. The kit sets out a protocol with a default for each
  choice the registration leaves open; the tool draws the sample by keys anyone can recompute (SHA-256 of seed and
  address), prints the hash for the deposit, and `--check` confirms the file on each scoring date.
- `tools/liveness.py`: the default window is 365 days, F27's "not updated for 12 months" (it was 180, which would
  have retired products F27 counts as alive). `tools/name_race.py` counts OpenAlex in title and abstract and Crossref
  in the title, as the frozen rule of the race of names says (OpenAlex's plain search also read full texts: 642 works
  for "agent manager" in 2026 against 18 in title and abstract, on 10 October 2026); `tools/names-table-a2.txt` (new)
  lists every candidate of Table A2 for the annual race. `tests/test_tools_follow_registration.py` (new) ties both
  tools to the frozen words.
- `tools/paper_sync.py` (new): checks the paper against the repository (listings, worked example, Tables 4 and A6,
  counts, named files, figures) whenever the tests run beside the paper.
- `pilot/prolific_to_long.py`: plain labels R001, R002, ... always, never a hash of a Prolific ID (the salt is in the
  file); new column `competency_answer`, so the wrong answers to the question of the trade can be counted.
- `record_card.py`: the count line printed "8 needed needed"; it prints "(8 needed)" again.
- `figures/figure_a1_calendar.py` (new): draws Figure A1 from `predictions/predictions.csv`, as its note in the paper
  says it is drawn, in the published order of rows; it adds the two commitments due before any check, the F27
  sample frozen on Zenodo by 31 December 2026 and every Set B protocol registered by 30 June 2027. The paper embeds
  `figure-A1-calendar-v2`.
- `tools/guarantor_record.py` (new, Section 7.2): the guarantor's record the paper proposes, computed from the
  ledger of `templates/guarantor-record.md` (now also a CSV, with `examples/guarantor-ledger.csv` and the lines it
  must print): products vouched for, how many lived 6 and 12 months, failures by severity, the median life of
  those that ended, and one weighted number only with weights the reader states. `kits/guarantor-signoff.md` keeps
  its ledger in the same columns.
- `tools/verify_record.py` (new, Sections 6.2 and 10.3): the receiving side of a portable record. Given the record of
  `record_card.py --format json` and the log, it says whether the log is the file that was scored, whether the
  scorer is the same, and whether rescoring on the record's date gives the same record, field by field; MATCH or
  every difference, exit code 0 only on a full match. A log with its failed piece removed shows at once (C4: Day
  becomes below Hour and the gain step x2 becomes x5, the route "hiding failures" of Table 3).
- `predictions/score.py` and `skill.py`: the status `not_conducted` that the registration sets for a Set B
  prediction whose protocol is not registered by 30 June 2027. It is accepted for Set B rows only and only after
  their deadline, listed on the scorecard as a failure of the testing programme, left out of the first Brier score
  and scored as wrong in a second one, and counted in the worst bound (Sections 11.2 and 11.4, Appendix D).
  `skill.py` refuses an unknown status and a scorecard that drops a prediction, as `score.py` does.
- Fixes after an independent review of the tools added that day, each with a test in `tests/test_review_fixes.py`:
  in a file saved with semicolons, `record_card.py` and `checker.html` read 0.125 as 125 (a dot before three digits
  was taken for thousands); 1.030,5 and 0,5 and 8.5 are read as written, and a bare 1.030 is refused with a message
  instead of being guessed. `tools/reference_hours.py` rounded 7.98 hours up to 8, which `horizon.py` counts as Day;
  it now never rounds across a rung threshold, and takes a third estimate only when the first two disagree.
  `tools/explain.py` named the wrong piece, or none, when a rung lapses under the 91-day rule, and promised slack
  from Week up that a single missed planted error takes away; both now follow the rule. `tools/too_clean.py` let one
  self-reviewed pass hide a log with no failure, and now reads the spreadsheet log. `tools/planted.py` counted
  " omission" under no kind and let a second outcome row undo a miss. `pilot/prolific_to_long.py` reads the unit
  in any case and the one written in the answer ("90 min"), drops answers with a minus sign, a numeral such as 1/2
  written as one character, days or weeks, and writes text that Python would still read as a number ("1e3") with
  the prefix "text: " so that the registered rule drops it; plain labels are now given in a random order, because
  in the order of the salted hashes (with the salt in the file) anyone holding an ID could estimate its label.
  `pilot/table_g2.py` keeps the row of a domain in which nobody was kept. `checker.html` reads a Windows-1252 file as
  `record_card.py` does. `tools/paper_sync.py` also checks the words of every row of Table A6 against the
  registered table; the two rows the paper words differently on purpose (F4a and F4b, the Gartner forecast cited
  through the Tray.ai summary) are declared in the tool and in the note under the table. `power.py`, `planted.py`,
  `screen_compare.py`, `table_g2.py`, `prolific_to_long.py`, `explain.py`, `record_card.py` and `too_clean.py` give
  a message instead of a traceback on impossible numbers, short rows, a byte order mark or a date such as 09.10.2026.
- A JSON log with `"passed": "yes"` or `"irreversible": "no"` was scored without a word, and wrongly: in Python and in
  JavaScript the text "no" counts as true. `record_card.py` (and so `tools/explain.py`, `tools/too_clean.py`,
  `tools/verify_record.py` and `audit_sample.py`, which read logs through it) and `checker.html` now name the line
  and ask for true or false without quotes; `horizon.py` itself is unchanged, as printed in the paper. Both sides
  read a number of a spreadsheet only when it is written plainly in the digits 0 to 9 (Python took 1_000 and digits
  of other scripts, the page took 0x10). `pilot/table_g2.py` prints the primary share with three decimals, so 0.6996
  no longer shows as "0.70 (not met)", and gives no ICC instead of a crash when every estimate is the same;
  `pilot/screen_compare.py` counts the wrong answers by option, so "eight of the 11 reversed the debit and the
  credit" (Appendix G2) can be recomputed.

## 1.0.0 (2026-10-09)

- `sources/claims.csv`: the evidence register filled with 14 rechecked claims (primary or secondary source,
  quote, archived copy, period, population, measure, who checked); README merged.
- Cross-references aligned with the paper: predictions F27 and F31 (old ids N1, N7), pilot status in Appendix E;
  prediction probabilities marked as draft probabilities, fixed on the registration date.
- Registered probabilities: each prediction's probability fixed on 9 October 2026 as the median of three blind
  model forecasts, adopted by the author (22 of 41 changed; `predictions/changelog-v1-v2.md`).
- `horizon.py` and `brier.py`: the listings of Appendix C2 and C3, byte for byte (a test checks SHA-256).
- Rules v1.1, from a desk pre-pilot of the thresholds (simulated logs and exact binomial rates; `pilot/`):
  - Month needs six pieces in 365 days, at least five verified (was four of four, which made Month harder to
    earn than Quarter at every pass rate).
  - Another model family alone never verifies an irreversible piece.
  - A piece with outside help counts as an attempt, never as verified.
  - Optional fields `task_id`, `model`, `tools`, `checker`, `rater_hours`, `audit`, `revoked`; a failed audit or
    a revoked piece is unverified; raters more than 1.5 times apart print `needs third rater`.
  - `started` is expected on every line; logs without it still score, with a warning.
  - Output shows the count next to the rung, the kinds of check and the median accepted size; `--stable` labels
    the rung against the score 91 days earlier.
- `record_card.py`: record line and card (text, Markdown, portable JSON) from a JSON Lines or spreadsheet log.
- `export-record.schema.json`: portable record format with hashes of the log and the scorer (Section 10.3).
- `audit_sample.py`: reproducible random sample of accepted pieces for a second check (Table 3).
- `examples/team-log.*`: a team of four across five domains, with Week, planted errors and a missed one.
- `predictions/`: the dated predictions of Table A6, version 2 (41 rows, sets A and B, families of linked
  predictions, model forecasts beside each probability), as a DRAFT frozen at OSF registration; resolution rules,
  files for resolving specific predictions, archived baselines, `score.py` and `skill.py`.
- `checker.html`: the scorer in an offline browser page, tested against `horizon.py`.
- `kits/` and `tools/`: one kit or tool per section of the paper (map in `kits/README.md`); `sources/` with a monthly
  archiving workflow; `integrations/claude-code-hook/`; `pilot/`: the desk pre-pilot and the live pilot protocol.
- Tests run on every push for Python 3.9 to 3.13.
