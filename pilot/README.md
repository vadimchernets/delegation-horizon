# The pilots of the thresholds (Appendices E and G2 of the paper)

Two kinds of test of the rules of Section 5.2. The desk pre-pilot (Appendix E) tested everything that can be tested
without people: simulated logs, exact rates and model raters. The Prolific pre-pilot (Appendix G2), registered on OSF
before any data were collected (DOI [10.17605/OSF.IO/V92R8](https://doi.org/10.17605/OSF.IO/V92R8)), asks working
professionals to rate the reference hours of the task bank. The protocol of the live pilot with people comes last.

## Desk pre-pilot (Appendix E): no people

| File | What it does |
|---|---|
| `simulate_rules.py` | Operating characteristics of the rung rules, calling `horizon.py` unchanged; sensitivity of the Day rule to the count (8, 10, 12) and share (0.7, 0.8, 0.9); rater noise at the Day boundary. Seed 20261009. |
| `rater_agreement.py` | Agreement of blind raters of reference hours (pairs within x1.5, ICC(2,1) on log hours, same rung size) and error against measured human times. |
| `task-bank-v0.csv`, `task-bank-v0.md` | 30 tasks in three low-risk domains with a statement of done, a hidden check and planted errors from Week up. Synthetic data only. |
| `metr-anchor-tasks.csv` | 14 public task identifiers with measured human baseline times from METR's public time-horizon data (release 1.1, `runs.jsonl`). |
| `results/` | Every number quoted in Appendix E. `model-ratings.csv` holds the blind estimates of four model raters from four families. |

## Prolific pre-pilot (Appendix G2): ratings by people

| File | What it does |
|---|---|
| `human_raters.py` | The registered analysis: exclusions, pairs within x1.5 against the 0.70 threshold, the same after removing each rater's level, ICC(2,1), test-retest, each task's median against its intended rung. Filed on OSF before data; never edited. |
| `registered-SHA256.txt` | SHA-256 of the files filed with that registration, as OSF reports them: `human_raters.py`, `rater_agreement.py` (which it imports) and `task-bank-v0.csv`. `cd pilot && shasum -a 256 -c registered-SHA256.txt`; the plan itself (PLAN.md) is on OSF. |
| `prolific_to_long.py` | Turns the Prolific Survey Builder exports into the long CSV the analysis reads. Reads each estimate as written, in the unit written in the answer or chosen beside it, keeps an answer with no number, with several ("8-12"), with a minus sign or in days as text so the registered rule drops it, lists every answer that is not a plain number with `--report`, and always writes plain labels R001, R002, ... in a random order, never an ID or a hash of one, so the file can be published (`--relabel` is still accepted). |
| `table_g2.py` | Table G2 of the paper, with every agreement figure from the functions of `human_raters.py`, called unchanged; adds who was excluded and why, and the four model raters of Appendix E on the same tasks (their pooled 56% on the 20 tasks). |
| `screen_compare.py` | The comparison that was not registered: raters whom the question of the trade stopped against those it kept, with an exact interval for the share stopped, each task's median in both groups and a seeded permutation test on the Week tasks (Sections 6.2 and 6.5). |
| `demo/` | Two synthetic exports in the Prolific format (26 made-up participants, including answers such as ".5", "1,200" minutes and "8-12"), so the whole chain can be run before the real, anonymised data are added. |

Run on the demo, or on the real exports in their place:

```
python3 pilot/prolific_to_long.py ratings-long.csv bookkeeping=pilot/demo/prolific-demo-bookkeeping.jsonl webtools=pilot/demo/prolific-demo-webtools.jsonl --report
python3 pilot/human_raters.py ratings-long.csv pilot/task-bank-v0.csv
python3 pilot/table_g2.py ratings-long.csv
python3 pilot/screen_compare.py ratings-long.csv
```

## The live pilot

| File | What it does |
|---|---|
| `pilot-protocol.md`, `preregistration-draft.md`, `consent-template.md` | The calibration pilot with people, ready for registration. |

Reproduce the desk pre-pilot:

```
python3 pilot/simulate_rules.py
python3 pilot/rater_agreement.py pilot/results/model-ratings.csv pilot/metr-anchor-tasks.csv
python3 -m unittest tests.test_pilot
```

What the desk pre-pilot shows: how the rules behave for a person of known reliability, where they invert, and how
far model raters agree. The Prolific pre-pilot shows how far working professionals agree on reference hours. How
people behave under the rules, and whether rungs predict new work, is what the live pilot measures.
