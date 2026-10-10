# Predictions

**Status: registered on OSF on 9 October 2026, DOI 10.17605/OSF.IO/VW6P9 (https://osf.io/vw6p9); frozen.** The files the registration lists with SHA-256 hashes (predictions.csv, resolution-rules.md, snapshots.csv, changelog-v1-v2.md and resolve/) keep the word DRAFT in their headings: they are frozen byte for byte, so their hashes still match the registration. The registration, not those headings, gives their status.

`predictions.csv` holds the dated predictions of Table A6 of the paper (Appendix D; Table 4 gives the ten core ones), one row each: the wording, the measure, the
baseline, the check and final dates, the probability, the rules for came true, did not and unresolved, the fallback
source, the nearest prior forecast, and who resolves it (a public source or a separately preregistered study).

The probabilities were fixed on 9 October 2026 as the median of three blind model forecasts, adopted by the author (changelog-v1-v2.md); every change is kept in the git history. On 9 October 2026 the table was
frozen at registration, the OSF DOI was added here and in the main README, and `TABLE_STATUS` in
`score.py` now names the registration. The table is never edited: a new prediction is
registered separately and carries its own date.

Scoring: copy `outcomes-template.csv`, fill in each status and the evidence, and run
`python3 predictions/score.py your-outcomes.csv`. The scorer refuses a file that drops or adds a prediction, takes
probabilities only from this table, and never counts an unresolved prediction as a success.
