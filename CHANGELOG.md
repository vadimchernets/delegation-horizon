# Changelog

## 1.0.0 (2026-10-09)

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
- `audit_sample.py`: reproducible random sample of accepted pieces for a second check (Table 4a).
- `examples/team-log.*`: a team of four across five domains, with Week, planted errors and a missed one.
- `predictions/`: the dated predictions of Table 6 as a DRAFT, frozen at OSF registration, and the scorecard tool.
- Tests run on every push for Python 3.9 to 3.13.
