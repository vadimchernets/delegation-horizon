# Figures

Scripts that draw figures of the paper from this repository, so a figure can be checked against what it shows.

| File | Paper | What it draws |
|---|---|---|
| `figure_a1_calendar.py` | Figure A1 (Appendix D), cited from Section 11.4 | The calendar of checks, one row per prediction of `predictions/predictions.csv`: checks, final dates, the annual scorecards, and the two commitments due before any check (the F27 sample frozen on Zenodo by 31 December 2026, and every Set B protocol registered by 30 June 2027) |
| `figure_a4_checking_process.py` | Figure A4 (Appendix F), cited from Sections 6.5 and 10.5 | The four steps of the checking process of Section 6.5, what each stands in for, what each earns under rules v1.1 (read from `horizon.py`, so a change of the rules shows in the figure) and where each stops |

```
python3 figures/figure_a1_calendar.py --out figure-A1-calendar-v2
python3 figures/figure_a4_checking_process.py --out figure-A4-checking-process
```

Each writes a `.png` (3000 pixels wide for Figure A1, 24 cm at the paper's size; 2000 pixels, 16 cm, for Figure A4)
and an `.svg`, the same bytes on every run. These scripts need matplotlib; nothing else in the repository does, and the tests skip them when it is
not installed.
