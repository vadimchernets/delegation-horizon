#!/usr/bin/env python3
"""simulate_rules.py: operating characteristics of the rung rules (desk pre-pilot).

Teaches: how often a person with a given true pass rate earns each rung under the
rules of Section 5.2, how often the verdict repeats in the next window, how many
simulated logs change rung when the count and the share move, and how rater noise
moves pieces across a rung's size. No human participants: every log here is simulated.
Limits: the true pass rate is assumed constant and pieces independent; real people
learn, tire and choose tasks. The scorer itself (horizon.py) is called unchanged;
only its constants are swapped for the variants under test.
Usage: python3 pilot/simulate_rules.py [--reps 20000] [--seed 20261009] [--out pilot/results]
Licence: MIT
"""
import argparse
import csv
import datetime as dt
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get("HORIZON_DIR", str(ROOT)))
import horizon  # noqa: E402  (the scorer of Appendix C, unchanged)

AS_OF = dt.date(2026, 10, 9)
P_GRID = [0.6, 0.7, 0.8, 0.9, 0.95]
# rule sets: rung -> (reference hours, minimum pieces, window days)
V1 = {"Hour": (1.0, 10, 91), "Day": (8.0, 10, 91), "Week": (40.0, 6, 182),
      "Month": (160.0, 4, 365), "Quarter": (500.0, 3, 365)}
V11 = dict(V1, Month=(160.0, 6, 365))
CANDIDATES_MONTH = [4, 5, 6, 7]       # Month counts considered in 365 days


def binom_at_least(n, k, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def needed(n, share):
    """Passes needed among n pieces under a pass share (horizon.py compares passes/n >= share)."""
    return math.ceil(n * share - 1e-9)


def exact(n, p, share=0.8):
    return binom_at_least(n, needed(n, share), p)


def make_log(rng, p, hours, n, days, planted=True):
    """n pieces of exactly `hours`, evenly spread over the window, the last on the as-of date."""
    pieces = []
    for i in range(n):
        date = AS_OF - dt.timedelta(days=int(i * (days - 1) / n))
        pieces.append({"date": date, "reference_hours": hours, "passed": rng.random() < p,
                       "check": "hidden_tests", "agent_saw_check": False, "irreversible": False,
                       "planted_errors": 1 if (planted and i == n - 1) else 0, "planted_missed": 0,
                       "outside_help": False, "revoked": False, "audit": "none"})
    return pieces


def full_rule(rng, p, hours, n, days, reps, share=0.8):
    """Monte Carlo through horizon.rung_holds (includes the recent-piece rule of upper rungs)."""
    old = horizon.PASS_SHARE
    horizon.PASS_SHARE = share
    try:
        hits = sum(horizon.rung_holds(make_log(rng, p, hours, n, days), hours, n, AS_OF, days)
                   for _ in range(reps))
    finally:
        horizon.PASS_SHARE = old
    return hits / reps


def crossing(n1, n2):
    """The true pass rate at which the two counts (share 0.8) swap order, or None."""
    sign = None
    for i in range(500, 1000):
        p = i / 1000
        d = exact(n1, p) - exact(n2, p)
        if sign is not None and (d > 0) != sign:
            return p
        sign = d > 0
    return None


def operating(reps, rng, out):
    rows = []
    for label, rules in (("v1", V1), ("v1.1", V11)):
        for rung, (hours, n, days) in rules.items():
            for p in P_GRID:
                e = exact(n, p)
                rows.append({"rules": label, "rung": rung, "count": n, "passes_needed": needed(n, 0.8),
                             "window_days": days, "true_pass_rate": p,
                             "p_earn_binomial": round(e, 4),
                             "p_earn_full_rule": round(full_rule(rng, p, hours, n, days, reps), 4),
                             "p_same_verdict_next_window": round(e * e + (1 - e) ** 2, 4),
                             "p_earn_two_windows_running": round(e * e, 4)})
    write(out / "operating-characteristic.csv", rows)
    month = [{"month_count": n, "passes_needed": needed(n, 0.8), "true_pass_rate": p,
              "p_earn": round(exact(n, p), 4)} for n in CANDIDATES_MONTH for p in P_GRID]
    write(out / "month-candidates.csv", month)
    return rows


def sensitivity(reps, rng, out):
    """Simulated logs at the Day rung: count in window 6..16, true pass rate 0.5..1.0."""
    logs = []
    for _ in range(reps):
        p = rng.uniform(0.5, 1.0)
        n = rng.randint(6, 16)
        logs.append(make_log(rng, p, 8.0, n, 91, planted=False))

    def verdicts(minimum, share):
        old = horizon.PASS_SHARE
        horizon.PASS_SHARE = share
        try:
            return [horizon.rung_holds(log, 8.0, minimum, AS_OF, 91) for log in logs]
        finally:
            horizon.PASS_SHARE = old

    base = verdicts(10, 0.8)
    rows = []
    for minimum in (8, 10, 12):
        for share in (0.7, 0.8, 0.9):
            v = verdicts(minimum, share)
            changed = sum(a != b for a, b in zip(base, v)) / len(v)
            rows.append({"minimum_count": minimum, "pass_share": share,
                         "share_earning_day": round(sum(v) / len(v), 4),
                         "share_changing_verdict_vs_10_0.8": round(changed, 4),
                         "gained": round(sum((not a) and b for a, b in zip(base, v)) / len(v), 4),
                         "lost": round(sum(a and (not b) for a, b in zip(base, v)) / len(v), 4)})
    write(out / "sensitivity-day.csv", rows)
    return rows


def rater_noise(reps, rng, out, within=0.8, ratio=1.5, threshold=8.0):
    """Unbiased raters whose pairs fall within x1.5 in `within` of cases; reference = geometric mean of two."""
    z = 1.2815515655446004 if within == 0.8 else None
    if z is None:
        from statistics import NormalDist
        z = NormalDist().inv_cdf(0.5 + within / 2)
    sigma = math.log(ratio) / z / math.sqrt(2)          # sd of one rater's log error
    sd_mean = sigma / math.sqrt(2)                      # sd of the mean of two
    rows = []
    for true in (6.0, 7.0, 7.5, 8.5, 9.0, 10.0):
        from statistics import NormalDist
        nd = NormalDist(0, sd_mean)
        analytic = 1 - nd.cdf(math.log(threshold / true))
        mc = sum(math.exp(math.log(true) + (rng.gauss(0, sigma) + rng.gauss(0, sigma)) / 2) >= threshold
                 for _ in range(reps)) / reps
        rows.append({"true_hours": true, "p_counted_at_or_above_8h_analytic": round(analytic, 4),
                     "p_counted_at_or_above_8h_mc": round(mc, 4), "rater_log_sd": round(sigma, 4)})
    write(out / "rater-noise-day.csv", rows)
    return rows


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    op = operating(args.reps, rng, out)
    sens = sensitivity(min(args.reps, 10000), rng, out)
    noise = rater_noise(args.reps, rng, out)
    print("P(earn rung), binomial | full rule via horizon.py, true pass rate 0.8:")
    for r in op:
        if r["true_pass_rate"] == 0.8:
            print(f"  {r['rules']:5} {r['rung']:8} {r['passes_needed']}/{r['count']} in {r['window_days']}d:"
                  f" {r['p_earn_binomial']:.3f} | {r['p_earn_full_rule']:.3f};"
                  f" same verdict next window {r['p_same_verdict_next_window']:.3f}")
    print(f"Week 5/6 and Day 8/10 swap order at p = {crossing(6, 10)} (below it Week is the easier rung)")
    print(f"Month 6 (5/6) and Quarter 3/3 swap order at p = {crossing(3, 6)}; Month 4/4 is harder than Quarter 3/3 at every p")
    print("Sensitivity at Day (simulated logs):")
    for r in sens:
        print(f"  count {r['minimum_count']:2}, share {r['pass_share']}: earn {r['share_earning_day']:.3f},"
              f" change {r['share_changing_verdict_vs_10_0.8']:.3f}")
    print("Rater noise at the Day boundary (80% of rater pairs within x1.5):")
    for r in noise:
        print(f"  true {r['true_hours']:>4} h -> counted as Day-size {r['p_counted_at_or_above_8h_analytic']:.3f}")


if __name__ == "__main__":
    main()
