# Changelog

## 1.0.0 (2026-10-09)

- `sources/claims.csv`: the evidence register filled with 14 rechecked claims (primary or secondary source,
  quote, archived copy, period, population, measure, who checked); README merged.
- Cross-references aligned with the paper: predictions F27 and F31 (old ids N1, N7), pilot status in Appendix E;
  prediction probabilities marked as draft probabilities, fixed on the registration date.
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
