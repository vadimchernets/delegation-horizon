# Kits and tools: from each section of the paper to something you can use today

Every section of the paper that has a practical consequence has a file here that a person or an
organisation can use the same day. Markdown kits need nothing but a text editor; the Python tools need
Python 3.9 or later and no packages; `checker.html` opens in any browser without a network.

| Paper section | Kit or tool | For | What it does |
|---|---|---|---|
| 1-2 Evidence, 13 Sources | `../sources/claims.csv`, `../tools/archive_urls.py` | researchers, journalists | Register of every claim with its source and a dated archived copy; refreshed monthly by a workflow |
| 3 Names | `../tools/name_race.py`, `../tools/names-table-a2.txt` | researchers, HR analysts | Yearly counts of every candidate name of Table A2 in OpenAlex (title and abstract) and Crossref (title), as the frozen rule of the race of names says (F9, F31) |
| 4 Tokens as seniority | `ai-usage-in-reviews.md` | HR, managers | Policy template: do not rank by tokens; what to look at instead |
| 5 The measure | `../horizon.py`, `../record_card.py`, `../checker.html` | everyone with a log | Score a work log; make a card; check a log in the browser with the same rules |
| 5.1 Reference hours | `reference-hours-raters.md`, `../tools/reference_hours.py` | employers, researchers, anyone logging | Choose, admit and brief two raters; turn their estimates into reference hours, or call a third rater |
| 5.2 The log | `acceptance-card.md`, `../tools/log_piece.py`, `../integrations/claude-code-hook/` | people who hand work to agents | State "done" before the hand-over; write log lines by answering questions; open a log entry automatically after each agent session so failures are not forgotten |
| 5.2-5.3 Reading a rung | `../tools/explain.py` | people with a log, employers | Why a log earns its rung: each condition, the slack, the day the rung lapses if nothing new is logged, and what the next rung needs |
| 5.8 Gaming and defences | `audit-checklist.md`, `planted-errors-guide.md`, `../tools/planted.py`, `../tools/too_clean.py`, `../tools/verify_record.py`, `VOUCHED.md` | organisations, auditors | Audit a record; plant wrong entries and omissions, seal the list by hash and score it by kind; flag logs that look too clean |
| 6 Background neutrality | `matched-task-study.md`, `../tools/power.py` | researchers, organisations | Protocol for comparing groups on the same tasks with the same agents and blind checks; how many people it needs |
| 6.2 Gates | `trade-screen.md`, `../tools/gate_leak.py` | researchers, employers | Admit people by a question of the trade rather than a label; how much a gate that admits by a label leaks |
| 6.2 Postings | `../tools/degree_share.py` | HR analysts, researchers | Share of your own postings that require a degree, by month or job family |
| 6.5 Newcomers who check by process | `checking-process.md` | people new to a trade | The four steps of Section 6.5 and what each earns in the log |
| 10.5 Process or experience | `process-vs-experience-study.md`, `../tools/process_study.py` | researchers | The comparison of Section 10.5 as a protocol to register, and its analysis with omissions and wrong entries apart |
| 7 Trust, the guarantor | `guarantor-signoff.md`, `../tools/guarantor_record.py`, `../tools/liveness.py` | guarantors, platforms | One-page sign-off; the guarantor's record from the ledger of products vouched for (how many, how long each lived, failures by severity); liveness of a frozen sample of products (F27: retired when unreachable or not updated for 12 months) |
| 11.4 The F27 sample | `f27-sample.md`, `../tools/freeze_sample.py` | whoever freezes the F27 sample, and anyone checking the scorecards | The protocol for the sample F27 needs on Zenodo by 31 December 2026, with a default for each open choice, and the draw by a key revealed only after the closed pool is registered (commit, then reveal), sealed with its SHA-256 on OSF |
| 7.1 Vouching | `VOUCHED.md` | maintainers, platforms | Template for admitting newcomers through a voucher |
| 8 Two markets | `release-checklist-by-risk.md` | product authors | What to do before release, by who will use the product |
| 9 Crossing over | `coding-codebook.md`, `../tools/kappa.py` | researchers | Codebook for Table A5 and two-coder agreement |
| 10.1 Employers and HR | `hiring-test/` | employers, HR | A paid one-day work test in the candidate's domain, with a blind rater and a posting without a degree requirement |
| 12 Security | `../tools/prerelease-check.sh` | product authors | Runs free secret and vulnerability scanners if installed, then six questions no scanner answers |
| 12-13 Scope | `scope-statement.md` | anyone printing a rung | What a rung means and does not mean, to attach beside it |

## Two ideas described here and not implemented
Section 10.2 suggests that schools teach acceptance before syntax, and Section 10.4 suggests that
onboarding products replace the "beginner or programmer" split with one question about what a person
can already hand over and check; both are left as ideas in the paper, since materials for them would
be teaching content rather than research instruments.

## Tests
`python3 -m unittest -v` from the repository root runs the tests of every tool, including a comparison
of `checker.html` with `horizon.py` on the worked example and on random logs (when Node.js is present).
No test touches the network.
