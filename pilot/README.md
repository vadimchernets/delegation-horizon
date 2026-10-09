# Desk pre-pilot of the thresholds (Appendix E of the paper)

Everything that can be tested about the rung thresholds without people, and the protocol for the
pilot with people. No human participants took part in anything in this folder.

| File | What it does |
|---|---|
| `simulate_rules.py` | Operating characteristics of the rung rules, calling `horizon.py` unchanged; sensitivity of the Day rule to the count (8, 10, 12) and share (0.7, 0.8, 0.9); rater noise at the Day boundary. Seed 20261009. |
| `rater_agreement.py` | Agreement of blind raters of reference hours (pairs within x1.5, ICC(2,1) on log hours, same rung size) and error against measured human times. |
| `task-bank-v0.csv`, `task-bank-v0.md` | 30 tasks in three low-risk domains with a statement of done, a hidden check and planted errors from Week up. Synthetic data only. |
| `metr-anchor-tasks.csv` | 14 public task identifiers with measured human baseline times from METR's public time-horizon data (release 1.1, `runs.jsonl`). |
| `results/` | Every number quoted in Appendix E. `model-ratings.csv` holds the blind estimates of four model raters from four families. |
| `pilot-protocol.md`, `preregistration-draft.md`, `consent-template.md` | The live pilot, ready for registration. |

Reproduce:

```
python3 pilot/simulate_rules.py
python3 pilot/rater_agreement.py pilot/results/model-ratings.csv pilot/metr-anchor-tasks.csv
python3 -m unittest tests.test_pilot
```

What this shows: how the rules behave for a person of known reliability, where they invert, and how
far model raters agree. What it does not show: how people behave, whether rungs predict new work, or
whether human raters agree. Those need the live pilot.
