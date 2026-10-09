# Contributing

Issues are welcome: bug reports, errors, questions, and logs that the scorer reads in a way you did not expect.
Please say what you ran, what you expected and what you saw. Replace every real name with a pseudonymous label and
remove private text before you post a log.

`horizon.py` and `brier.py` are byte-for-byte listings of the paper's Appendix C2 and C3, and a test checks it.
A correction to either goes into the paper first and then here. Pull requests to the other files (the card, the
templates, the scorecard tool, the tests) are welcome; they must keep to the Python standard library and must not
change what the two listings compute.

`predictions/predictions.csv` holds the frozen predictions. It is never edited after registration: a new
prediction is registered separately and carries its own date.

Security problems go through a private report, not an issue: see `SECURITY.md`.
