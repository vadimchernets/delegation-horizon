#!/usr/bin/env python3
"""human_raters.py: the Prolific pre-pilot of reference hours (registered 9 October 2026).

Reads a long CSV of human ratings and applies the registered rules, in this order:
  1. exclude a participant who failed the attention check or the competency question;
  2. drop an estimate that is not a positive number or is above 2000 hours;
  3. per domain, for every task, every pair of remaining raters: is the larger estimate
     at most 1.5 times the smaller? The primary outcome is the pooled share of such pairs
     (threshold 0.70, from the pilot protocol);
  4. the same share after removing each rater's personal level (mean log deviation from
     the task medians), which shows what calibration on anchor tasks could buy;
  5. ICC(2,1) on log hours over raters who answered every task of their domain;
  6. test-retest: share of participants whose two answers to the repeated task are within 1.5;
  7. for each task, the median estimate and the rung it falls in, against the rung the
     task bank intended.
Input columns: domain, rater, task_id, reference_hours, attention_ok, competency_ok
(the repeated task carries task_id with the suffix "-retest").
Usage: python3 pilot/human_raters.py ratings-long.csv [pilot/task-bank-v0.csv]
Licence: MIT
"""
import csv
import itertools
import math
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from rater_agreement import icc21  # noqa: E402

RUNGS = [(1, "Hour"), (8, "Day"), (40, "Week"), (160, "Month"), (500, "Quarter")]
THRESHOLD = 0.70


def rung(hours):
    name = "below Hour"
    for floor, label in RUNGS:
        if hours >= floor:
            name = label
    return name


def load(path):
    rows, excluded = [], set()
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["attention_ok"].strip() != "1" or r["competency_ok"].strip() != "1":
                excluded.add((r["domain"], r["rater"]))
                continue
            try:
                h = float(r["reference_hours"])
            except ValueError:
                continue
            if 0 < h <= 2000:
                rows.append((r["domain"], r["rater"], r["task_id"], h))
    return rows, excluded


def pair_share(by_task):
    hit = tot = 0
    for raters in by_task.values():
        for a, b in itertools.combinations(raters.values(), 2):
            tot += 1
            hit += max(a, b) / min(a, b) <= 1.5
    return (hit / tot if tot else float("nan")), tot


def calibrated(by_task):
    med = {t: statistics.median(r.values()) for t, r in by_task.items()}
    dev = defaultdict(list)
    for t, r in by_task.items():
        for who, h in r.items():
            dev[who].append(math.log(h) - math.log(med[t]))
    level = {who: statistics.mean(d) for who, d in dev.items()}
    return {t: {who: math.exp(math.log(h) - level[who]) for who, h in r.items()}
            for t, r in by_task.items()}


def main():
    rows, excluded = load(sys.argv[1])
    bank = {}
    if len(sys.argv) > 2:
        with open(sys.argv[2], encoding="utf-8") as fh:
            bank = {r["task_id"]: r.get("target_rung", "") for r in csv.DictReader(fh)}
    for domain in sorted({d for d, *_ in rows}):
        main_tasks, retest = defaultdict(dict), defaultdict(dict)
        for d, who, task, h in rows:
            if d != domain:
                continue
            (retest if task.endswith("-retest") else main_tasks)[task.replace("-retest", "")][who] = h
        raters = {w for r in main_tasks.values() for w in r}
        share, pairs = pair_share(main_tasks)
        cshare, _ = pair_share(calibrated(main_tasks))
        tasks = sorted(main_tasks)
        complete = [w for w in sorted(raters) if all(w in main_tasks[t] for t in tasks)]
        icc = icc21([[math.log(main_tasks[t][w]) for w in complete] for t in tasks]) if len(complete) > 1 else float("nan")
        rt = [(main_tasks[t][w], h) for t, r in retest.items() for w, h in r.items() if w in main_tasks[t]]
        rt_share = sum(max(a, b) / min(a, b) <= 1.5 for a, b in rt) / len(rt) if rt else float("nan")
        n_excl = sum(1 for d, _ in excluded if d == domain)
        print(f"\n== {domain}: {len(raters)} raters kept, {n_excl} excluded, {pairs} rater pairs over {len(tasks)} tasks")
        print(f"pairs within x1.5: {share:.3f}  (registered threshold {THRESHOLD:.2f}: {'met' if share >= THRESHOLD else 'not met'})")
        print(f"pairs within x1.5 after removing each rater's level: {cshare:.3f}")
        print(f"ICC(2,1) on log hours, {len(complete)} complete raters: {icc:.3f}")
        print(f"test-retest within x1.5: {rt_share:.3f} (n={len(rt)})")
        print("task  median_h  rung  intended")
        for t in tasks:
            m = statistics.median(main_tasks[t].values())
            print(f"{t}  {m:8.1f}  {rung(m):10s}  {bank.get(t, '')}")


if __name__ == "__main__":
    main()
