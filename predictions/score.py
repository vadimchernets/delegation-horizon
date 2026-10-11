#!/usr/bin/env python3
"""score.py: build the annual scorecard of the frozen predictions from a file of outcomes.

Teaches: the scoring rules of Section 11.4 and Appendix D. Every registered prediction appears on the
scorecard, none may be dropped or added, the probability comes from the frozen table and never from the
outcomes file, and "unresolved" is never a success. The Brier score itself is computed by brier.py of
Appendix C3, unchanged.
Outcomes CSV columns: id,status,evidence,scored_on
  status: came_true, did_not, not_yet_due, unresolved or not_conducted (1 and 0 are accepted for came_true and
  did_not). not_conducted is a Set B prediction whose protocol was not registered by its deadline (30 June 2027):
  it is listed on every scorecard as a failure of the testing programme, left out of the first Brier score and
  scored as wrong in the second, so a study that is never run cannot drop out of the count (Section 11.2).
Usage: python3 predictions/score.py predictions/outcomes-2027.csv
       python3 predictions/score.py outcomes.csv --predictions predictions/predictions.csv [--as-of 2027-10-09]
Limits: it checks the bookkeeping, not the evidence; whether a threshold was met is decided by people
(and by models of two families, Appendix D) reading the frozen rules.        Licence: MIT
"""
import argparse
import contextlib
import csv
import datetime as dt
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import brier  # noqa: E402  (Appendix C3, byte for byte)

# Flipped to "frozen on OSF, doi:..." on the day the table is registered; until then it is a draft.
TABLE_STATUS = "registered on OSF on 9 October 2026, DOI 10.17605/OSF.IO/VW6P9 (https://osf.io/vw6p9); the table is frozen"
STATUS = {"came_true": "1", "1": "1", "did_not": "0", "0": "0",
          "not_yet_due": "not_yet_due", "unresolved": "unresolved", "": "not_yet_due",
          "not_conducted": "not_conducted"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def deadline(row):
    """The registration deadline of a Set B row, read from its frozen words ('... by 30 June 2027 ...')."""
    m = re.search(r"(\d{1,2}) ([A-Za-z]+) (\d{4})", row.get("registration_deadline") or "")
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS.index(m.group(2).lower()) + 1, int(m.group(1)))


def wrong(p):
    """The outcome that makes a forecast of p wrong: 0 for p of 0.5 or more, 1 below."""
    return "0" if float(p) >= 0.5 else "1"


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outcomes")
    ap.add_argument("--predictions", default=os.path.join(HERE, "predictions.csv"))
    ap.add_argument("--as-of", default=dt.date.today().isoformat(),
                    help="date of the scorecard, used where a row of the outcomes gives no scored_on")
    args = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(args.as_of)
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
            sys.exit(f"{pid}: status must be came_true, did_not, not_yet_due, unresolved or not_conducted")
        if status == "not_conducted":
            if frozen[pid].get("set", "").strip() != "B":
                sys.exit(f"{pid}: not_conducted applies to Set B only; a Set A prediction without data is unresolved")
            due = deadline(frozen[pid])
            try:
                day = dt.date.fromisoformat(r["scored_on"].strip()) if (r.get("scored_on") or "").strip() else as_of
            except ValueError:
                sys.exit(f"{pid}: scored_on must be a date written YYYY-MM-DD")
            if due is None or day <= due:
                sys.exit(f"{pid}: not conducted only after {due.day} {MONTHS[due.month - 1].title()} {due.year}"
                         if due else f"{pid}: the table gives no registration deadline for this prediction")
        seen[pid] = STATUS[status]
    missing = [pid for pid in frozen if pid not in seen]
    if missing:
        sys.exit("every frozen prediction must appear on the scorecard; missing: " + ", ".join(missing))
    counts = {}
    for code in seen.values():
        counts[code] = counts.get(code, 0) + 1
    not_conducted = [pid for pid in frozen if seen[pid] == "not_conducted"]
    first = [(pid, frozen[pid]["probability"], seen[pid]) for pid in frozen if pid not in not_conducted]
    brier_csv(first, brier.main)
    if not_conducted:
        print("not conducted, a failure of the testing programme: " + ", ".join(not_conducted))
        second = [(pid, frozen[pid]["probability"], wrong(frozen[pid]["probability"]) if pid in not_conducted
                   else seen[pid]) for pid in frozen]
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            brier_csv(second, brier.main)
        line = next((x for x in buf.getvalue().splitlines() if x.startswith("Brier score over")), "")
        m = re.match(r"Brier score over (\d+) resolved: ([0-9.]+)", line)
        if m:
            print(f"with every prediction not conducted scored as wrong: Brier score over {m.group(1)}: {m.group(2)}")
    print(f"came true: {counts.get('1', 0)}, did not: {counts.get('0', 0)}, "
          f"not yet due: {counts.get('not_yet_due', 0)}, unresolved: {counts.get('unresolved', 0)}, "
          f"not conducted: {counts.get('not_conducted', 0)} (of {len(frozen)} in the table)")


def brier_csv(rows, score):
    """Write id,probability,outcome in the order given and score it with brier.py of Appendix C3, unchanged."""
    fd, tmp = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "probability", "outcome"])
            w.writerows(rows)
        score(tmp)
    finally:
        os.remove(tmp)


if __name__ == "__main__":
    main()
