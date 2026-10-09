# Changelog

## 1.0.0 (2026-10-09)

- `horizon.py` and `brier.py`: the listings of Appendix C2 and C3, byte for byte (a test checks SHA-256).
- `record_card.py`: record line and card (text, Markdown, portable JSON) from a JSON Lines or spreadsheet log.
- `export-record.schema.json`: portable record format with hashes of the log and the scorer (Section 10.3).
- `audit_sample.py`: reproducible random sample of accepted pieces for a second check (Table 4a).
- `examples/team-log.*`: a team of four across five domains, with Week, planted errors and a missed one.
- `predictions/`: the dated predictions of Table 6 as a DRAFT, frozen at OSF registration, and the scorecard tool.
- Tests run on every push for Python 3.9 to 3.13.
