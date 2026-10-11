#!/usr/bin/env python3
"""screen_compare.py: the comparison of Appendix G2 that was not registered: raters a question of the trade stopped,
against the raters it kept.

Teaches: what a gate that admits by a label lets through (Section 6.2), measured on the people it admitted. For each
domain it prints how many attentive participants answered the competency question wrongly, with an exact 95%
interval; each task's median estimate in both groups; and, for the tasks the bank meant for the Week rung, how far
apart the two groups sit (the mean log ratio of their medians) with a seeded permutation test over raters. The
paper reports the bookkeeping sample this way: 11 of 60 answered wrongly, and their medians for BK08 to BK10 were 6,
6 and 8 hours against 8, 8 and 12 for the other 49.
Limits: exploratory, as the paper says; the registered outcomes are human_raters.py and table_g2.py. Estimates are
read by the registered rule (a positive number up to 2000 hours); participants who failed the attention check are
left out of both groups.
Usage: python3 pilot/screen_compare.py ratings-long.csv [--bank pilot/task-bank-v0.csv] [--reps 5000] [--seed 20261009]
Licence: MIT
"""
import argparse
import csv
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def tail(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def exact(k, n, level=0.95):
    """Clopper-Pearson interval for k of n, by bisection on the binomial tail (Section 5.8 uses exact intervals)."""
    if n == 0:
        return float("nan"), float("nan")
    a = (1 - level) / 2

    def solve(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) < target else (lo, mid)
        return (lo + hi) / 2
    low = 0.0 if k == 0 else solve(lambda p: tail(k, n, p), a)
    high = 1.0 if k == n else solve(lambda p: tail(k + 1, n, p), 1 - a)
    return low, high


def show(xs):
    return f"{statistics.median(xs):.3g} h ({len(xs)})" if xs else "n/a"


def load(path):
    """domain -> rater -> (competency_ok, {task: hours}), attentive participants only, estimates by the registered rule."""
    out = defaultdict(dict)
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["attention_ok"].strip() != "1":
                continue
            entry = out[r["domain"]].setdefault(r["rater"], [r["competency_ok"].strip() == "1", {}])
            try:
                h = float(r["reference_hours"])
            except ValueError:
                continue
            if 0 < h <= 2000 and not r["task_id"].endswith("-retest"):
                entry[1][r["task_id"]] = h
    return out


def wrong_answers(path):
    """domain -> option -> number of attentive participants who chose that wrong option (one per participant)."""
    seen, out = set(), defaultdict(lambda: defaultdict(int))
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (r["domain"], r["rater"])
            if key in seen or r["attention_ok"].strip() != "1" or r["competency_ok"].strip() == "1":
                continue
            seen.add(key)
            out[r["domain"]][(r.get("competency_answer") or "").strip() or "(no answer)"] += 1
    return out


def gap(raters, failed, tasks):
    """Mean over tasks of log(median of kept / median of failed); positive when the failed rate tasks smaller."""
    logs = []
    for t in tasks:
        kept = [est[t] for who, (_, est) in raters.items() if who not in failed and t in est]
        lost = [est[t] for who, (_, est) in raters.items() if who in failed and t in est]
        if kept and lost:
            logs.append(math.log(statistics.median(kept) / statistics.median(lost)))
    return statistics.mean(logs) if logs else float("nan")


def compare(raters, week_tasks, reps, seed):
    failed = {who for who, (ok, _) in raters.items() if not ok}
    observed = gap(raters, failed, week_tasks)
    if not failed or len(failed) == len(raters) or math.isnan(observed):
        return observed, float("nan")
    rng = random.Random(seed)
    names = sorted(raters)
    hits = 0
    for _ in range(reps):
        shuffled = set(rng.sample(names, len(failed)))
        hits += abs(gap(raters, shuffled, week_tasks)) >= abs(observed) - 1e-12
    return observed, (hits + 1) / (reps + 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Raters a question of the trade stopped, against those it kept "
                                             "(exploratory, not registered).")
    ap.add_argument("ratings", help="long CSV written by prolific_to_long.py")
    ap.add_argument("--bank", default=str(HERE / "task-bank-v0.csv"))
    ap.add_argument("--reps", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261009)
    args = ap.parse_args(argv)
    if args.reps < 1:
        ap.error("--reps is the number of shuffles, 1 or more")
    try:
        with open(args.ratings, encoding="utf-8-sig") as fh:
            head = [h.strip() for h in (csv.DictReader(fh).fieldnames or [])]
    except OSError as err:
        ap.exit(1, f"{args.ratings}: {err.strerror}\n")
    missing = [c for c in ("domain", "rater", "task_id", "reference_hours", "attention_ok", "competency_ok")
               if c not in head]
    if missing:
        ap.exit(1, f"{args.ratings}: the header lacks {', '.join(missing)}; use the long CSV of prolific_to_long.py\n")
    with open(args.bank, encoding="utf-8") as fh:
        intended = {r["task_id"]: r["target_rung"] for r in csv.DictReader(fh)}
    print("Exploratory comparison, not registered (Appendix G2); attentive participants only.")
    answers = wrong_answers(args.ratings) if "competency_answer" in head else {}
    for domain, raters in sorted(load(args.ratings).items()):
        failed = sorted(who for who, (ok, _) in raters.items() if not ok)
        n, k = len(raters), len(failed)
        low, high = exact(k, n)
        print(f"\n== {domain}: {k} of {n} answered the question of the trade wrongly ({k / n:.0%}; "
              f"exact 95% interval {low:.1%} to {high:.1%})")
        if answers.get(domain):
            tally = sorted(answers[domain].items(), key=lambda kv: (-kv[1], kv[0]))
            print("wrong answers by option: " + ", ".join(f"{a!r} {c}" for a, c in tally))
        tasks = sorted({t for _, est in raters.values() for t in est})
        print("task  intended  median, wrong answer (n)  median, right answer (n)")
        for t in tasks:
            lost = [est[t] for who, (ok, est) in raters.items() if not ok and t in est]
            kept = [est[t] for who, (ok, est) in raters.items() if ok and t in est]
            print(f"{t}  {intended.get(t, ''):8}  {show(lost):24}  {show(kept)}")
        week = [t for t in tasks if intended.get(t) == "Week"]
        if week:
            g, p = compare(raters, week, args.reps, args.seed)
            ratio = "n/a" if math.isnan(g) else f"{math.exp(g):.2f}"
            pval = "n/a" if math.isnan(p) else f"{p:.3f}"
            print(f"Week tasks ({', '.join(week)}): median of the right answers over median of the wrong ones, "
                  f"geometric mean {ratio}; permutation p = {pval} ({args.reps} shuffles of the raters, seed {args.seed})")


if __name__ == "__main__":
    main()
