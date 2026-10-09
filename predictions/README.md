# Predictions

**Status: DRAFT, not yet registered; frozen at OSF registration.**

`predictions.csv` holds the dated predictions of Table A6 of the paper (Appendix D; Table 4 gives the ten core ones), one row each: the wording, the measure, the
baseline, the check and final dates, the probability, the rules for came true, did not and unresolved, the fallback
source, the nearest prior forecast, and who resolves it (a public source or a separately preregistered study).

Until registration the probabilities and wording may still change; every change is kept in the git history. On the
day of registration the table is frozen, the OSF DOI is added here and in the main README, and `TABLE_STATUS` in
`score.py` changes from DRAFT to the registration record. After that the table is never edited: a new prediction is
registered separately and carries its own date.

Scoring: copy `outcomes-template.csv`, fill in each status and the evidence, and run
`python3 predictions/score.py your-outcomes.csv`. The scorer refuses a file that drops or adds a prediction, takes
probabilities only from this table, and never counts an unresolved prediction as a success.
