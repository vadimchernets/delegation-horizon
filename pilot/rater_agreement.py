#!/usr/bin/env python3
"""rater_agreement.py: agreement and accuracy of blind raters of reference hours.

Teaches: how to check the rater rule of Section 5.1 before people are involved. Reads a
long CSV of ratings (task_id, rater, reference_hours) and reports, for every pair of raters,
the share of tasks whose two estimates lie within a ratio of 1.5; a two-way random-effects
intraclass correlation ICC(2,1) on log hours; and, for tasks with a measured human time,
each rater's error against it. In the desk pre-pilot the raters are language models of
different families, blind to each other and to the measured times: no human participants.
Limits: model raters are a stand-in for the two human raters of the rule, not evidence
about them.
Usage: python3 pilot/rater_agreement.py pilot/results/model-ratings.csv pilot/metr-anchor-tasks.csv
Licence: MIT
"""
import argparse
import csv
import itertools
import math
import statistics
from collections import defaultdict
from pathlib import Path


def load_ratings(path):
    ratings = defaultdict(dict)                     # task -> rater -> hours
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            h = float(r["reference_hours"])
            if h > 0:
                ratings[r["task_id"]][r["rater"]] = h
    return ratings


def load_truth(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as fh:
        return {r["task_id"]: float(r["reference_hours"]) for r in csv.DictReader(fh)}


BANDS = [(500.0, "Quarter"), (160.0, "Month"), (40.0, "Week"), (8.0, "Day"), (1.0, "Hour")]


def band(hours):
    """The rung whose size a piece reaches (largest threshold not above it)."""
    return next((name for h, name in BANDS if hours >= h), "below Hour")


def within(a, b, ratio=1.5):
    return max(a, b) / min(a, b) <= ratio + 1e-9


def icc21(matrix):
    """ICC(2,1), absolute agreement, single rater (Shrout and Fleiss), on a complete n x k matrix."""
    n, k = len(matrix), len(matrix[0])
    if n < 2 or k < 2:
        return float("nan")
    grand = sum(map(sum, matrix)) / (n * k)
    rows = [sum(r) / k for r in matrix]
    cols = [sum(r[j] for r in matrix) / n for j in range(k)]
    ssr = k * sum((m - grand) ** 2 for m in rows)
    ssc = n * sum((m - grand) ** 2 for m in cols)
    sst = sum((x - grand) ** 2 for r in matrix for x in r)
    sse = sst - ssr - ssc
    msr, msc, mse = ssr / (n - 1), ssc / (k - 1), sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)


def summarise(ratings, truth, tasks, label):
    raters = sorted({r for t in tasks for r in ratings[t]})
    out = []
    for a, b in itertools.combinations(raters, 2):
        both = [t for t in tasks if a in ratings[t] and b in ratings[t]]
        if both:
            share = sum(within(ratings[t][a], ratings[t][b]) for t in both) / len(both)
            med = statistics.median(max(ratings[t][a], ratings[t][b]) / min(ratings[t][a], ratings[t][b])
                                    for t in both)
            out.append({"set": label, "measure": "pair_within_x1.5", "who": f"{a} vs {b}",
                        "n": len(both), "value": round(share, 3), "median_ratio": round(med, 2)})
    complete = [t for t in tasks if all(r in ratings[t] for r in raters)]
    if complete and len(raters) >= 2:
        m = [[math.log(ratings[t][r]) for r in raters] for t in complete]
        out.append({"set": label, "measure": "ICC(2,1)_log_hours", "who": "all raters",
                    "n": len(complete), "value": round(icc21(m), 3), "median_ratio": ""})
        same = sum(len({band(ratings[t][r]) for r in raters}) == 1 for t in complete) / len(complete)
        out.append({"set": label, "measure": "same_rung_size_all_raters", "who": "all raters",
                    "n": len(complete), "value": round(same, 3), "median_ratio": ""})
        pairs = [(ratings[t][a], ratings[t][b]) for t in complete for a, b in itertools.combinations(raters, 2)]
        out.append({"set": label, "measure": "pair_within_x1.5", "who": "all pairs pooled",
                    "n": len(pairs), "value": round(sum(within(x, y) for x, y in pairs) / len(pairs), 3),
                    "median_ratio": round(statistics.median(max(x, y) / min(x, y) for x, y in pairs), 2)})
    judged = [t for t in tasks if t in truth]
    if judged:
        for r in raters + ["geometric mean of raters"]:
            errs = []
            for t in judged:
                if r == "geometric mean of raters":
                    vals = [math.log(v) for v in ratings[t].values()]
                    if not vals:
                        continue
                    est = math.exp(sum(vals) / len(vals))
                elif r in ratings[t]:
                    est = ratings[t][r]
                else:
                    continue
                errs.append(est / truth[t])
            if errs:
                out.append({"set": label, "measure": "within_x1.5_of_measured", "who": r, "n": len(errs),
                            "value": round(sum(within(e, 1.0) for e in errs) / len(errs), 3),
                            "median_ratio": round(math.exp(statistics.median(math.log(e) for e in errs)), 2)})
                out.append({"set": label, "measure": "within_x2_of_measured", "who": r, "n": len(errs),
                            "value": round(sum(within(e, 1.0, 2.0) for e in errs) / len(errs), 3),
                            "median_ratio": ""})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ratings")
    ap.add_argument("truth", nargs="?", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    ratings, truth = load_ratings(args.ratings), load_truth(args.truth)
    bank = sorted(t for t in ratings if not t.startswith("MT"))
    anchor = sorted(t for t in ratings if t.startswith("MT"))
    rows = summarise(ratings, truth, bank, "task bank v0 (statement of done)") + \
        summarise(ratings, truth, anchor, "measured-time anchor (identifier only)")
    out = Path(args.out) if args.out else Path(args.ratings).with_name("rater-agreement.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["set", "measure", "who", "n", "value", "median_ratio"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['set'][:22]:22} {r['measure']:26} {r['who']:28} n={r['n']:<3} {r['value']}"
              f"  {('median ratio ' + str(r['median_ratio'])) if r['median_ratio'] != '' else ''}")


if __name__ == "__main__":
    main()
