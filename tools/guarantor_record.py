#!/usr/bin/env python3
"""guarantor_record.py: the guarantor's record of Section 7.2, computed from the ledger of products vouched for.

Teaches: the paper proposes a measure for the guarantor too: "how many products they vouched for, how long each
lived, and how many failed, weighted by how badly" (Section 7.2). This turns the ledger of templates/guarantor-record.md
into that record, per guarantor and domain, on a date: products vouched for; of those vouched at least 6 months
(182 days) and 12 months (365 days) before the date, how many lived that long; failures by severity; and the median
life of the products that ended (retired or withdrawn). Failed products stay in the ledger and in the record.
Everything is counted as it stood on the date: a product that ended after --as-of is still live then, and a failure
counts from its failed_on date (optional column; without it, from ended_on; with neither, it is counted and marked
"date unknown").
Limits: it trusts the ledger. "Weighted by how badly" needs weights the paper does not fix: the counts by severity
are always printed, and one weighted number only when --weights gives the weights. Whether a product is still live
can be checked with tools/liveness.py.
Usage:
  python3 tools/guarantor_record.py examples/guarantor-ledger.csv --as-of 2026-10-09   # prints guarantor-expected.txt
  python3 tools/guarantor_record.py ledger.csv [--as-of 2026-12-31] [--weights minor=1,harmful=3,severe=10]
ledger.csv columns: guarantor, domain, product, vouched_on, status (live, retired or withdrawn), ended_on (empty
while live), severity (none, minor, harmful or severe); optional failed_on (the day of the failure); other columns (maker, checked, audience, ...) are kept as
notes. examples/guarantor-ledger.csv is a worked example and examples/guarantor-expected.txt what it must print.
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import statistics
import sys
from collections import Counter, defaultdict

NEED = ["guarantor", "domain", "product", "vouched_on", "status", "ended_on", "severity"]
STATUSES = ("live", "retired", "withdrawn")
SEVERITIES = ("none", "minor", "harmful", "severe")
SIX, TWELVE = 182, 365        # days: 6 and 12 months, as in the template's summary


def day(text, what, n):
    try:
        return dt.date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f"row {n}: {what} must be a date written YYYY-MM-DD, not {text!r}")


def load(path):
    """The ledger as a list of dicts with dates parsed; every rule of the template checked, row by row."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            rows = list(reader)
    except OSError as e:
        raise ValueError(f"cannot read {path}: {e.strerror}")
    missing = [c for c in NEED if c not in fields]
    if missing:
        raise ValueError(f"{path} lacks the column(s) {', '.join(missing)} (needed: {', '.join(NEED)})")
    out = []
    for n, r in enumerate(rows, 2):
        status, severity = r["status"].strip().lower(), r["severity"].strip().lower()
        if status not in STATUSES:
            raise ValueError(f"row {n}: status must be live, retired or withdrawn, not {r['status']!r}")
        if severity not in SEVERITIES:
            raise ValueError(f"row {n}: severity must be none, minor, harmful or severe, not {r['severity']!r}")
        vouched = day(r["vouched_on"], "vouched_on", n)
        ended = None
        if status == "live":
            if r["ended_on"].strip():
                raise ValueError(f"row {n}: a live product has no ended_on; give the status retired or withdrawn")
        else:
            if not r["ended_on"].strip():
                raise ValueError(f"row {n}: a {status} product needs ended_on, the day it ended")
            ended = day(r["ended_on"], "ended_on", n)
            if ended < vouched:
                raise ValueError(f"row {n}: ended_on {ended} is before vouched_on {vouched}")
        failed = None
        if (r.get("failed_on") or "").strip():
            failed = day(r["failed_on"], "failed_on", n)
        elif severity != "none":
            failed = ended
        out.append({**r, "guarantor": r["guarantor"].strip(), "domain": r["domain"].strip(), "status": status,
                    "severity": severity, "vouched": vouched, "ended": ended, "failed": failed})
    return out


def summarise(rows, as_of):
    """One record per guarantor and domain, on the date as_of."""
    groups = defaultdict(list)
    for r in rows:
        if r["vouched"] <= as_of:                       # a product vouched later is not yet in the record
            groups[(r["guarantor"], r["domain"])].append(r)
    out = []
    for (guarantor, domain), items in sorted(groups.items()):
        def life(r):
            end = r["ended"] if r["ended"] is not None and r["ended"] <= as_of else as_of
            return (end - r["vouched"]).days
        def lived(days):
            eligible = [r for r in items if (as_of - r["vouched"]).days >= days]
            return sum(life(r) >= days for r in eligible), len(eligible)
        live_6, eligible_6 = lived(SIX)
        live_12, eligible_12 = lived(TWELVE)
        ended = [life(r) for r in items if r["ended"] is not None and r["ended"] <= as_of]
        failures = [r for r in items if r["severity"] != "none" and (r["failed"] is None or r["failed"] <= as_of)]
        sev = Counter(r["severity"] for r in failures)
        undated = sum(r["failed"] is None for r in failures)
        def status_on(r):                               # a product that ended after as_of was still live then
            return r["status"] if r["ended"] is not None and r["ended"] <= as_of else "live"
        out.append({"guarantor": guarantor, "domain": domain, "vouched": len(items),
                    "live_6": live_6, "eligible_6": eligible_6, "live_12": live_12, "eligible_12": eligible_12,
                    "severity": {s: sev.get(s, 0) for s in SEVERITIES[1:]},
                    "status": {s: sum(status_on(r) == s for r in items) for s in STATUSES}, "undated": undated,
                    "median_ended": statistics.median(ended) if ended else None,
                    "quarter": f"{as_of.year}-Q{(as_of.month - 1) // 3 + 1}"})
    return out


def parse_weights(text):
    weights = {}
    for part in text.split(","):
        name, _, value = part.partition("=")
        name = name.strip().lower()
        if name not in SEVERITIES[1:]:
            raise ValueError(f"--weights: {name!r} is not a severity (minor, harmful, severe)")
        try:
            weights[name] = float(value)
        except ValueError:
            raise ValueError(f"--weights: the weight of {name} must be a number, not {value!r}")
    missing = [s for s in SEVERITIES[1:] if s not in weights]
    if missing:
        raise ValueError(f"--weights: give a weight for {', '.join(missing)} too")
    return weights


def lines(s, weights=None):
    sev = s["severity"]
    first = (f"{s['guarantor']}: {s['domain']} . {s['vouched']} vouched . live at 6 months {s['live_6']}/{s['eligible_6']}, "
             f"at 12 months {s['live_12']}/{s['eligible_12']} . failures {sev['minor']} minor, {sev['harmful']} harmful, "
             f"{sev['severe']} severe" + (f" ({s['undated']} date unknown)" if s.get("undated") else "") +
             f" . {s['quarter']}")
    st = s["status"]
    median = "none ended yet" if s["median_ended"] is None else f"{s['median_ended']:g} days"
    second = (f"  status: {st['live']} live, {st['retired']} retired, {st['withdrawn']} withdrawn; "
              f"median life of the products that ended: {median}")
    if weights:
        total = sum(weights[k] * sev[k] for k in sev)
        second += (f"; weighted failures {total:g} (minor {weights['minor']:g}, harmful {weights['harmful']:g}, "
                   f"severe {weights['severe']:g})")
    return [first, second]


def main(argv=None):
    ap = argparse.ArgumentParser(description="The guarantor's record of Section 7.2, from a ledger of products vouched for.")
    ap.add_argument("ledger", help="CSV ledger (see templates/guarantor-record.md)")
    ap.add_argument("--as-of", default=dt.date.today().isoformat(), help="date of the record (default today)")
    ap.add_argument("--weights", help="one weighted number for failures, for example minor=1,harmful=3,severe=10")
    args = ap.parse_args(argv)
    try:
        as_of = day(args.as_of, "--as-of", 0)
        weights = parse_weights(args.weights) if args.weights else None
        records = summarise(load(args.ledger), as_of)
    except ValueError as e:
        sys.exit(f"guarantor_record.py: {e}")
    if not records:
        sys.exit("guarantor_record.py: no product was vouched for on or before the date")
    for s in records:
        print("\n".join(lines(s, weights)))


if __name__ == "__main__":
    main()
