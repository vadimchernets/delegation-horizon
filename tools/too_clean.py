#!/usr/bin/env python3
"""too_clean.py: flag work logs that look too clean to be true, so an auditor knows where to look first.

Teaches: Table 3 lists ways to game the measure. Several leave a statistical trace in the log itself:
no failure at all, sizes bunched just above a rung threshold, attention minutes that never vary,
upper-rung pieces with no planted errors, or checks the scorer does not count. This prints, per
person and domain, which traces are present.
Limits: a flag is a reason to audit, never a verdict. Careful people do have clean months. The
thresholds below are starting points, stated here so that anyone can change them in the open.
Usage:
  python3 tools/too_clean.py work-log.jsonl [--as-of 2026-10-09] [--min-pieces 10]
Exit code 0 when nothing is flagged, 1 when something is (handy in an audit script).
Licence: MIT
"""
import argparse
import datetime as dt
import os
import statistics
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import horizon  # noqa: E402

JUST_ABOVE = 0.10          # a size within 10% above a rung threshold counts as "just above"
JUST_ABOVE_SHARE = 0.5     # flag when at least half of the pieces sit just above a threshold
FLAT_CV = 0.10             # flag when attention minutes vary by less than 10% (coefficient of variation)
WEAK_CHECK_SHARE = 0.5     # flag when at least half of the pieces use a check that never verifies


def flags(pieces, min_pieces):
    out = []
    n = len(pieces)
    if n < min_pieces:
        return out
    if all(horizon.verified(r) for r in pieces):
        out.append(f"no failed, rejected or abandoned piece among {n}")
    thresholds = [hours for _, hours, *_ in horizon.RUNGS]
    near = sum(any(t <= float(r["reference_hours"]) < t * (1 + JUST_ABOVE) for t in thresholds) for r in pieces)
    if near / n >= JUST_ABOVE_SHARE:
        out.append(f"{near} of {n} pieces sit just above a rung threshold")
    minutes = [float(r["attention_minutes"]) for r in pieces]
    mean = statistics.mean(minutes)
    if mean > 0 and statistics.pstdev(minutes) / mean < FLAT_CV:
        out.append("attention minutes barely vary between pieces")
    big = [r for r in pieces if float(r["reference_hours"]) >= horizon.PLANTED_FROM]
    if big and not any(int(r["planted_errors"]) > 0 for r in big):
        out.append(f"{len(big)} piece(s) of Week size or more, none with a planted error")
    weak = sum(r["check"] not in horizon.INDEPENDENT for r in pieces)
    if weak / n >= WEAK_CHECK_SHARE:
        out.append(f"{weak} of {n} pieces checked by same_family, self_review or none")
    if len({r["date"] for r in pieces}) == 1:
        out.append("all pieces closed on one day (logged after the fact?)")
    return out


def main():
    ap = argparse.ArgumentParser(description="Flag work logs that look too clean.")
    ap.add_argument("log")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--min-pieces", type=int, default=10, help="skip people with fewer pieces in the year")
    args = ap.parse_args()
    as_of = dt.date.fromisoformat(args.as_of)
    groups = defaultdict(list)
    for r in horizon.load(args.log):
        if as_of - dt.timedelta(days=365) < r["date"] <= as_of:
            groups[(r["person"], r["domain"])].append(r)
    found = False
    for (person, domain), pieces in sorted(groups.items()):
        f = flags(pieces, args.min_pieces)
        status = "audit first" if f else "no trace"
        print(f"{person}: {domain}: {status}" + "".join(f"\n  - {x}" for x in f))
        found = found or bool(f)
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
