#!/usr/bin/env python3
"""score.py: build the annual scorecard of the frozen predictions from a file of outcomes.

Teaches: the scoring rules of Section 11.4 and Appendix D. Every registered prediction appears on the
scorecard, none may be dropped or added, the probability comes from the frozen table and never from the
outcomes file, and "unresolved" is never a success. The Brier score itself is computed by brier.py of
Appendix C3, unchanged.
Outcomes CSV columns: id,status,evidence,scored_on
  status: came_true, did_not, not_yet_due or unresolved (1 and 0 are accepted for came_true and did_not)
Usage: python3 predictions/score.py predictions/outcomes-2027.csv
       python3 predictions/score.py outcomes.csv --predictions predictions/predictions.csv
Limits: it checks the bookkeeping, not the evidence; whether a threshold was met is decided by people
(and by models of two families, Appendix D) reading the frozen rules.        Licence: MIT
"""
import argparse
import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import brier  # noqa: E402  (Appendix C3, byte for byte)

# Flipped to "frozen on OSF, doi:..." on the day the table is registered; until then it is a draft.
TABLE_STATUS = "registered on OSF on 9 October 2026, DOI 10.17605/OSF.IO/VW6P9 (https://osf.io/vw6p9); the table is frozen"
STATUS = {"came_true": "1", "1": "1", "did_not": "0", "0": "0",
          "not_yet_due": "not_yet_due", "unresolved": "unresolved", "": "not_yet_due"}


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outcomes")
    ap.add_argument("--predictions", default=os.path.join(HERE, "predictions.csv"))
    args = ap.parse_args(argv)
    print(f"prediction table: {TABLE_STATUS}")
    frozen = {r["id"]: r for r in read(args.predictions)}
    seen = {}
    for r in read(args.outcomes):
        pid = r["id"].strip()
        if pid in seen:
            sys.exit(f"{pid}: listed twice in the outcomes")
        if pid not in frozen:
            sys.exit(f"{pid}: not in the frozen table (later predictions are registered and scored separately)")
        status = r.get("status", "").strip().lower()
        if status not in STATUS:
            sys.exit(f"{pid}: status must be came_true, did_not, not_yet_due or unresolved")
        seen[pid] = STATUS[status]
    missing = [pid for pid in frozen if pid not in seen]
    if missing:
        sys.exit("every frozen prediction must appear on the scorecard; missing: " + ", ".join(missing))
    counts = {}
    for code in seen.values():
        counts[code] = counts.get(code, 0) + 1
    fd, tmp = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "probability", "outcome"])
            for pid in frozen:                      # the order of the frozen table
                w.writerow([pid, frozen[pid]["probability"], seen[pid]])
        brier.main(tmp)
    finally:
        os.remove(tmp)
    print(f"came true: {counts.get('1', 0)}, did not: {counts.get('0', 0)}, "
          f"not yet due: {counts.get('not_yet_due', 0)}, unresolved: {counts.get('unresolved', 0)} "
          f"(of {len(frozen)} in the table)")


if __name__ == "__main__":
    main()
