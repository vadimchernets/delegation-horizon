# Predictions

**Status: registered on OSF on 9 October 2026, DOI 10.17605/OSF.IO/VW6P9 (https://osf.io/vw6p9); frozen.** The files the registration lists with SHA-256 hashes (predictions.csv, resolution-rules.md, snapshots.csv, changelog-v1-v2.md and resolve/) keep the word DRAFT in their headings: they are frozen byte for byte, so their hashes still match the registration. The registration, not those headings, gives their status.

`predictions.csv` holds the dated predictions of Table A6 of the paper (Appendix D; Table 4 gives the ten core ones), one row each: the wording, the measure, the
baseline, the check and final dates, the probability, the rules for came true, did not and unresolved, the fallback
source, the nearest prior forecast, and who resolves it (a public source or a separately preregistered study).

The probabilities were fixed on 9 October 2026 as the median of three blind model forecasts, adopted by the author (changelog-v1-v2.md); every change is kept in the git history. On 9 October 2026 the table was
frozen at registration, the OSF DOI was added here and in the main README, and `TABLE_STATUS` in
`score.py` now names the registration. The table is never edited: a new prediction is
registered separately and carries its own date.

**Check that nothing moved.** `registered-SHA256.txt` is the manifest filed with the registration (OSF file
`resolve-SHA256.txt`, unchanged; its own SHA-256 is `07810eb7bee9f1e125b6dab87a68361362ec8ffae02f88fe8f241f382ba50c24`).
Names starting with `./` are in `resolve/`; `resolve.zip` exists only on OSF. `python3 -m unittest tests.test_registered`
compares every file with it, or by hand: `cd predictions && shasum -a 256 predictions.csv resolution-rules.md` and
`cd resolve && shasum -a 256 *.md`.

**Set B, from a study's estimates.** `set_b.py` applies the frozen came-true and did-not rules of the nine Set B
predictions written on a confidence interval (F2, F3, F3b, F4a, F4b, F7, F12, F26, F34) to the estimates a separately
registered study produces. `python3 predictions/set_b.py verdict estimates.csv` (columns id, estimate, lower, upper,
plus level day or week_up for the two F7 rows) prints each estimate and interval, the verdict, and the frozen rule
texts read from `predictions.csv`, whose SHA-256 it checks against the registered one; only the numeric thresholds
are written in the script, and `tests/test_set_b.py` checks each against the frozen words. An interval that meets
neither rule is unresolved, except for F12, whose did-not rule is "otherwise". From counts, `diff` gives a difference
of two shares in points with the Newcombe hybrid score interval, and `or` the Mantel-Haenszel odds ratio over strata
with the Robins-Breslow-Greenland interval (90% by default, for F7); with `--id`, each also applies the rule. The
sample sizes of Section 11.2 are `../tools/power.py`.

**The F27 sample.** F27 is unresolved unless its sample is frozen on Zenodo by 31 December 2026:
`../kits/f27-sample.md` is the protocol and `../tools/freeze_sample.py` draws and seals it.

Scoring: copy `outcomes-template.csv`, fill in each status and the evidence, and run
`python3 predictions/score.py your-outcomes.csv`. The scorer refuses a file that drops or adds a prediction, takes
probabilities only from this table, and never counts an unresolved prediction as a success.
