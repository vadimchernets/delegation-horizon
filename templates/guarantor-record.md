# Guarantor record

A guarantor puts their name under a product made by someone else and answers for it to their own circle (Section
7.2 of the paper). The record below is the guarantor's natural measure: how many products they vouched for, how
long each lived, and how many failed, weighted by how badly. Keep every product you vouched for, including the ones
that failed: a record without its failures says nothing.

| Field | Meaning |
|---|---|
| Guarantor | A name or a stable public label |
| Domain | Where the guarantor's word carries weight |
| Record as of | Date (ISO format) |

## Products vouched for

| # | Product | Maker (label) | Vouched on | What was checked before vouching | Audience it was vouched to | Status | Ended on | Failure and severity (none, minor, harmful, severe) | What the guarantor did about it |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | live / retired / withdrawn | | | |

Kept as a spreadsheet, the table above becomes a CSV with one row per product and the columns `guarantor`,
`domain`, `product`, `maker`, `vouched_on`, `status` (live, retired or withdrawn), `ended_on` (empty while live) and
`severity` (none, minor, harmful or severe); further columns, such as what was checked, the audience and what the
guarantor did, are kept as notes. `examples/guarantor-ledger.csv` is a worked example.

## Summary (recompute at every update)

`python3 tools/guarantor_record.py ledger.csv --as-of 2026-12-31` (the worked example: `examples/guarantor-ledger.csv
--as-of 2026-10-09`) computes the summary below from that CSV, per
guarantor and domain; `--weights minor=1,harmful=3,severe=10` adds one weighted number for the failures, with weights
you state. "Still live after 6 months" counts, among the products vouched for at least 182 days before the date,
those that lived that long; the same with 365 days for 12 months.

| | |
|---|---|
| Products vouched for | |
| Still live after 6 months / 12 months | |
| Failures, by severity | |
| Median life of the products that ended (retired or withdrawn) | |
| Liability terms or insurance, if any | |
