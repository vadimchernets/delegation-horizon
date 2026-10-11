#!/usr/bin/env python3
"""skill.py: the extra scores of Section 11.4 that score.py does not print.

Teaches: how a set of probabilities is judged beyond one Brier number. For the resolved predictions it gives
the Brier score overall, by set (A public, B research programme) and by family of linked predictions; the
share resolved; the Brier score with every Set B prediction not conducted scored as if the forecast had been
wrong; a worst bound in which every prediction past its final date and still unresolved, and every prediction
not conducted, is scored as if the forecast had been wrong; and the Brier skill score against reference
forecasts (a flat 0.5, the pooled model forecasters, and a market price where one exists).
Usage: python3 predictions/skill.py outcomes.csv [--predictions predictions/predictions.csv] [--today 2028-12-31]
Outcomes CSV columns: id,status,evidence,scored_on (status: came_true, did_not, not_yet_due, unresolved or
not_conducted, the last for Set B only and only after its registration deadline, 30 June 2027)
Limits: stdlib only; family scores count a family once (mean over its members), so linked predictions do not
inflate the count. Licence: MIT
"""
import argparse
import csv
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OK = {"came_true": 1, "1": 1, "did_not": 0, "0": 0}
OTHER = {"unresolved", "not_yet_due", "not_conducted"}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                       "august", "september", "october", "november", "december"], 1)}


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def parse_date(text):
    """'31 December 2028' -> date; anything else -> None."""
    m = re.fullmatch(r"\s*(\d{1,2}) ([A-Za-z]+) (\d{4})\s*", text or "")
    if not m or m.group(2).lower() not in MONTHS:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))


def brier(pairs):
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs) if pairs else None


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if 0.0 <= v <= 1.0 else None


def wrong(p):
    """The outcome that makes a forecast of p wrong."""
    return 0 if p >= 0.5 else 1


def deadline(row):
    """The registration deadline of a Set B row, read from its frozen words ('... by 30 June 2027 ...')."""
    m = re.search(r"(\d{1,2} [A-Za-z]+ \d{4})", row.get("registration_deadline") or "")
    return parse_date(m.group(1)) if m else None


def scores(preds, outcomes, today):
    res, worst, not_done, by_set, by_fam = [], [], [], {}, {}
    refs = {"flat_0.5": [], "models": [], "market": []}
    for r in preds:
        p = num(r["probability"])
        if p is None:
            raise ValueError(f"{r['id']}: probability missing or outside 0..1")
        st = outcomes.get(r["id"], "not_yet_due")
        if st not in OK and st not in OTHER:
            raise ValueError(f"{r['id']}: status must be came_true, did_not, not_yet_due, unresolved or not_conducted")
        if st == "not_conducted":
            due = deadline(r)
            if (r.get("set") or "").strip() != "B":
                raise ValueError(f"{r['id']}: not_conducted applies to Set B only")
            if due is None or today <= due:
                raise ValueError(f"{r['id']}: not conducted only after its registration deadline ({due})")
            not_done.append((p, wrong(p)))
            worst.append((p, wrong(p)))          # a study never run is scored as if the forecast had been wrong
        elif st in OK:
            o = OK[st]
            res.append((p, o))
            worst.append((p, o))
            by_set.setdefault(r.get("set", "A") or "A", []).append((p, o))
            by_fam.setdefault(r.get("family") or r["id"], []).append((p - o) ** 2)
            refs["flat_0.5"].append((p, o, 0.5))
            m = num(r.get("models_geomean_odds"))
            if m is not None:
                refs["models"].append((p, o, m))
            k = num(r.get("market_price"))
            if k is not None:
                refs["market"].append((p, o, k))
        elif st == "unresolved":
            final = parse_date(r.get("final_date", ""))
            if final and today > final:
                worst.append((p, wrong(p)))   # scored as if the forecast had been wrong
    out = {"n": len(preds), "resolved": len(res), "share_resolved": len(res) / len(preds) if preds else 0,
           "brier": brier(res), "not_conducted": len(not_done),
           "brier_not_conducted_as_wrong": brier(res + not_done), "brier_worst_bound": brier(worst),
           "brier_by_set": {k: brier(v) for k, v in sorted(by_set.items())},
           "brier_by_family": sum(sum(v) / len(v) for v in by_fam.values()) / len(by_fam) if by_fam else None,
           "skill": {}}
    for name, triples in refs.items():
        if triples:
            b = brier([(p, o) for p, o, _ in triples])
            ref = brier([(q, o) for _, o, q in triples])
            out["skill"][name] = None if not ref else 1 - b / ref
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outcomes")
    ap.add_argument("--predictions", default=os.path.join(HERE, "predictions.csv"))
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)
    preds = read(a.predictions)
    ids = {r["id"] for r in preds}
    outcomes = {}
    for r in read(a.outcomes):
        if r["id"] not in ids:
            sys.exit(f"{r['id']}: not in the frozen table")
        outcomes[r["id"]] = (r.get("status") or "not_yet_due").strip().lower()
        if outcomes[r["id"]] not in OK and outcomes[r["id"]] not in OTHER:
            sys.exit(f"{r['id']}: status must be came_true, did_not, not_yet_due, unresolved or not_conducted")
    missing = [r["id"] for r in preds if r["id"] not in outcomes]
    if missing:
        sys.exit("every frozen prediction must appear on the scorecard; missing: " + ", ".join(missing))
    try:
        s = scores(preds, outcomes, dt.date.fromisoformat(a.today))
    except ValueError as err:
        sys.exit(str(err))
    for k, v in s.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
